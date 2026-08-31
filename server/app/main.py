import os
import json
import shutil
import datetime
import asyncio
from typing import List, Optional

from fastapi import FastAPI, Depends, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .db import init_db, get_db
from .models import Worker, Task, Message, TaskPhoto
from .translate import translate_text
from .claude_review import review_task
from .photo_review import verify_photo
from .whatsapp import send_whatsapp_message
from .push import send_task_push

MANAGER_LANGUAGE = "he"  # your friend's default language, change as needed

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Where CI drops the latest built APK + a small version-metadata JSON file
# that the app polls to check for updates. Served directly as static files
# so /apk/latest.apk and /apk/latest.json "just work" once uploaded.
APK_DIR = "apk_releases"
os.makedirs(APK_DIR, exist_ok=True)

# Shared secret CI must send to be allowed to publish a new APK build.
# Set APK_UPLOAD_SECRET in /etc/site-comms.env on the server and as a
# matching GitHub Actions repo secret of the same name. If this isn't set
# on the server, uploads are refused rather than silently left open.
APK_UPLOAD_SECRET = os.environ.get("APK_UPLOAD_SECRET")

app = FastAPI(title="Site Comms Server")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

init_db()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


# ---------- Live console (WebSocket) ----------

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, payload: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager_console = ConnectionManager()


@app.websocket("/ws/console")
async def console_socket(websocket: WebSocket):
    await manager_console.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # console doesn't need to send anything, just keep-alive
    except WebSocketDisconnect:
        manager_console.disconnect(websocket)


# ---------- Worker registration ----------

@app.post("/workers/register")
async def register_app_worker(
    name: str = Form(...),
    language: str = Form(...),
    device_token: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    photo_url = None
    if photo:
        fname = f"{name.replace(' ', '_')}_{datetime.datetime.utcnow().timestamp()}_{photo.filename}"
        path = os.path.join(UPLOAD_DIR, fname)
        with open(path, "wb") as f:
            shutil.copyfileobj(photo.file, f)
        photo_url = f"/uploads/{fname}"

    worker = Worker(
        name=name, language=language, photo_url=photo_url,
        channel="app", device_token=device_token,
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)

    await manager_console.broadcast({
        "type": "worker_registered",
        "worker": {"id": worker.id, "name": worker.name, "language": worker.language,
                    "channel": worker.channel, "photo_url": worker.photo_url},
    })
    return {"id": worker.id, "name": worker.name}


@app.post("/workers/{worker_id}/device_token")
async def update_device_token(
    worker_id: str,
    device_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """App calls this whenever FCM hands it a fresh token (on first launch,
    and any time the token rotates - FCM tokens aren't permanent)."""
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(404, "Worker not found")
    worker.device_token = device_token
    db.commit()
    return {"id": worker.id, "device_token": worker.device_token}


@app.post("/workers/whatsapp")
async def add_whatsapp_worker(
    name: str = Form(...),
    phone: str = Form(...),
    language: str = Form(...),
    db: Session = Depends(get_db),
):
    worker = Worker(name=name, phone=phone, language=language, channel="whatsapp")
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return {"id": worker.id, "name": worker.name}


@app.get("/workers")
def list_workers(db: Session = Depends(get_db)):
    workers = db.query(Worker).all()
    return [
        {"id": w.id, "name": w.name, "language": w.language, "channel": w.channel,
         "photo_url": w.photo_url, "phone": w.phone}
        for w in workers
    ]


@app.delete("/workers/{worker_id}")
async def delete_worker(worker_id: str, db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(404, "Worker not found")
    name = worker.name
    db.query(Task).filter(Task.worker_id == worker_id).delete()
    db.delete(worker)
    db.commit()
    await manager_console.broadcast({"type": "worker_removed", "worker_id": worker_id, "name": name})
    return {"ok": True, "id": worker_id}


# ---------- Tasks ----------

LOCATION_INSTRUCTIONS = {
    # First line prepended to the translated message, per location_mode.
    "pin": "Please go to the marked location on the building map.",
    "gps": "Please go to the marked location. Your phone will confirm you've arrived.",
    "photo_checkin": "Please go to the marked location and take a photo there before you begin. "
                      "Wait for approval before starting the task.",
}


@app.post("/tasks")
async def create_task(
    worker_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    detailed_description: Optional[str] = Form(None),
    manager_lang: str = Form(MANAGER_LANGUAGE),
    location_mode: str = Form("none"),          # 'none' | 'pin' | 'gps' | 'photo_checkin'
    floor: Optional[str] = Form(None),
    pin_x: Optional[str] = Form(None),
    pin_y: Optional[str] = Form(None),
    location_note: Optional[str] = Form(None),
    photo_requirement: Optional[str] = Form(None),  # e.g. "the cement blocks by the north wall"
    db: Session = Depends(get_db),
):
    if location_mode not in ("none", "pin", "gps", "photo_checkin"):
        raise HTTPException(400, "location_mode must be 'none', 'pin', 'gps', or 'photo_checkin'")

    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(404, "Worker not found")

    task = Task(worker_id=worker_id, title=title, description=description,
                detailed_description=detailed_description, status="assigned",
                location_mode=location_mode, floor=floor, pin_x=pin_x, pin_y=pin_y,
                location_note=location_note, photo_requirement=photo_requirement)
    db.add(task)
    db.commit()
    db.refresh(task)

    message_text = f"{title}\n{description}"
    location_line = LOCATION_INSTRUCTIONS.get(location_mode)
    if location_line and location_mode != "none":
        note = f" ({location_note})" if location_note else ""
        message_text = f"{location_line}{note}\n\n{message_text}"

    # App users translate on-device (ML Kit) - server just sends original text + a push notification.
    # WhatsApp users need server-side translation before sending.
    whatsapp_status = None
    if worker.channel == "whatsapp":
        try:
            def _translate_and_send():
                translated = translate_text(message_text, manager_lang, worker.language)
                result = send_whatsapp_message(worker.phone, translated)
                return translated, result
            translated, result = await asyncio.wait_for(
                asyncio.to_thread(_translate_and_send), timeout=25.0
            )
            db.add(Message(worker_id=worker.id, direction="to_worker",
                            original_text=message_text, original_lang=manager_lang,
                            translated_text=translated, translated_lang=worker.language))
            db.commit()
            whatsapp_status = result.get("status")
        except asyncio.TimeoutError:
            whatsapp_status = "timed_out"
        except Exception as e:
            # Task itself is already saved above — a translation/WhatsApp failure
            # (bad credentials, network issue, rate limit) must never block task
            # creation or hang the request.
            whatsapp_status = f"failed: {e}"
            print(f"[whatsapp:ERROR] task={task.id} worker={worker.id} -> {e}")
    else:
        try:
            push_result = send_task_push(worker.device_token, task.id, title)
            print(f"[push] task={task.id} worker={worker.id} -> {push_result}")
        except Exception as e:
            print(f"[push:ERROR] task={task.id} worker={worker.id} -> {e}")

    await manager_console.broadcast({
        "type": "task_created", "task_id": task.id, "worker_id": worker.id,
        "floor": task.floor, "pin_x": task.pin_x, "pin_y": task.pin_y,
        "location_mode": task.location_mode,
    })
    return {"id": task.id, "status": task.status, "whatsapp_status": whatsapp_status}


@app.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    return [
        {
            "id": t.id, "title": t.title, "description": t.description,
            "worker_id": t.worker_id, "status": t.status,
            "before_photo_urls": (t.before_photo_urls or "").split(",") if t.before_photo_urls else [],
            "after_photo_urls": (t.after_photo_urls or "").split(",") if t.after_photo_urls else [],
            "claude_review": t.claude_review,
            "photo_requirement": t.photo_requirement,
            "photos": [
                {
                    "id": p.id, "stage": p.stage, "url": p.url,
                    "ai_verdict": p.ai_verdict, "ai_explanation": p.ai_explanation,
                    "admin_override": p.admin_override,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in sorted(t.photos, key=lambda p: p.created_at or datetime.datetime.min)
            ],
            "location_mode": t.location_mode, "floor": t.floor,
            "pin_x": t.pin_x, "pin_y": t.pin_y, "location_note": t.location_note,
            "checkin_photo_url": t.checkin_photo_url, "checkin_approved": t.checkin_approved,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "in_progress_at": t.in_progress_at.isoformat() if t.in_progress_at else None,
            "done_at": t.done_at.isoformat() if t.done_at else None,
        }
        for t in tasks
    ]


async def _notify_worker_photo_feedback(db, worker, task, feedback_text: str, push_title: str):
    """Sends a 'this photo needs a retake' style message to a worker, via
    WhatsApp (translated) or logged for the app (translated on-device) plus
    a push. Shared by the automatic no_match path and the manager's manual
    'not ok' override, so both notify the worker the same way."""
    if worker.channel == "whatsapp":
        try:
            def _translate_and_send(text=feedback_text):
                translated = translate_text(text, MANAGER_LANGUAGE, worker.language)
                result = send_whatsapp_message(worker.phone, translated)
                return translated, result
            translated, _ = await asyncio.wait_for(asyncio.to_thread(_translate_and_send), timeout=25.0)
            db.add(Message(worker_id=worker.id, task_id=task.id, direction="to_worker",
                            original_text=feedback_text, original_lang=MANAGER_LANGUAGE,
                            translated_text=translated, translated_lang=worker.language))
        except Exception as e:
            print(f"[photo-feedback:ERROR] task={task.id} worker={worker.id} -> {e}")
    else:
        # App worker: on-device ML Kit translates this like it does task
        # text, so just log it - plus a push so it surfaces even if
        # they've already put the phone down.
        db.add(Message(worker_id=worker.id, task_id=task.id, direction="to_worker",
                        original_text=feedback_text, original_lang=MANAGER_LANGUAGE))
        try:
            send_task_push(worker.device_token, task.id, push_title)
        except Exception as e:
            print(f"[push:ERROR] task={task.id} worker={worker.id} -> {e}")


@app.post("/tasks/{task_id}/photo")
async def upload_task_photo(
    task_id: str,
    stage: str = Form(...),  # 'before' or 'after'
    photos: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    if stage not in ("before", "after"):
        raise HTTPException(400, "stage must be 'before' or 'after'")

    saved_urls = []
    saved_paths = []
    for photo in photos:
        fname = f"{task_id}_{stage}_{datetime.datetime.utcnow().timestamp()}_{photo.filename}"
        path = os.path.join(UPLOAD_DIR, fname)
        with open(path, "wb") as f:
            shutil.copyfileobj(photo.file, f)
        saved_urls.append(f"/uploads/{fname}")
        saved_paths.append(path)

    # Log every photo individually, and if the task specifies what the
    # photo should actually show, get an immediate AI verdict on each one -
    # this is separate from (and runs well before) the general before/after
    # review below, which only fires once, at the end.
    photo_reviews = []
    worker = task.worker
    for url, path in zip(saved_urls, saved_paths):
        task_photo = TaskPhoto(task_id=task.id, stage=stage, url=url)
        if task.photo_requirement:
            try:
                verdict_data = await asyncio.to_thread(
                    verify_photo, task.title, task.description, task.photo_requirement, path
                )
            except Exception as e:
                verdict_data = {"verdict": "unclear", "explanation": f"(AI review failed: {e})"}
            task_photo.ai_verdict = verdict_data["verdict"]
            task_photo.ai_explanation = verdict_data["explanation"]
        db.add(task_photo)
        db.flush()  # get task_photo.id without a separate commit
        photo_reviews.append({
            "id": task_photo.id, "url": url, "stage": stage,
            "verdict": task_photo.ai_verdict, "explanation": task_photo.ai_explanation,
        })

        # A clear mismatch gets sent back to the worker as feedback - framed
        # as "try again", never a harsh rejection, since this is meant to be
        # an iterative process.
        if task_photo.ai_verdict == "no_match":
            feedback_text = (
                f"That's not the correct item for \"{task.title}\". "
                f"Please take another photo of {task.photo_requirement}."
            )
            await _notify_worker_photo_feedback(db, worker, task, feedback_text, "Photo needs a retake")

    if stage == "before":
        existing = task.before_photo_urls.split(",") if task.before_photo_urls else []
        task.before_photo_urls = ",".join(existing + saved_urls)
        if task.status == "assigned":
            task.status = "in_progress"
            task.in_progress_at = datetime.datetime.utcnow()
    else:
        existing = task.after_photo_urls.split(",") if task.after_photo_urls else []
        task.after_photo_urls = ",".join(existing + saved_urls)
        task.status = "done"
        task.done_at = datetime.datetime.utcnow()

        # Kick off Claude review once the task is marked done
        try:
            before_paths = [os.path.join(UPLOAD_DIR, u.split("/uploads/")[-1])
                             for u in (task.before_photo_urls or "").split(",") if u]
            after_paths = [os.path.join(UPLOAD_DIR, u.split("/uploads/")[-1])
                            for u in (task.after_photo_urls or "").split(",") if u]
            if before_paths and after_paths:
                task.claude_review = review_task(task.title, task.description, before_paths, after_paths)
        except Exception as e:
            task.claude_review = f"(review failed: {e})"

    db.commit()
    db.refresh(task)

    await manager_console.broadcast({
        "type": "task_updated", "task_id": task.id, "status": task.status,
        "claude_review": task.claude_review, "photo_reviews": photo_reviews,
    })
    return {"id": task.id, "status": task.status, "claude_review": task.claude_review,
            "photo_reviews": photo_reviews}


@app.post("/tasks/{task_id}/photos/{photo_id}/override")
async def override_photo_verdict(
    task_id: str,
    photo_id: str,
    approved: bool = Form(...),  # True = admin says this photo IS correct, False = admin says it is NOT
    db: Session = Depends(get_db),
):
    """Manager overrides (or co-signs) the AI's verdict on a specific photo.
    A manual 'not ok' notifies the worker the same way an automatic
    no_match does - the AI's explanation isn't necessarily available or
    relevant here (a manager can override a match too), so this uses a
    simple, direct message instead."""
    task = db.query(Task).filter(Task.id == task_id).first()
    photo = db.query(TaskPhoto).filter(TaskPhoto.id == photo_id, TaskPhoto.task_id == task_id).first()
    if not task or not photo:
        raise HTTPException(404, "Task or photo not found")
    photo.admin_override = approved
    db.commit()
    db.refresh(photo)

    if approved is False:
        feedback_text = f"That photo isn't the correct item for \"{task.title}\". Please take another photo."
        if task.photo_requirement:
            feedback_text = (
                f"That photo isn't the correct item for \"{task.title}\". "
                f"Please take another photo of {task.photo_requirement}."
            )
        await _notify_worker_photo_feedback(db, task.worker, task, feedback_text, "Photo needs a retake")
        db.commit()

    await manager_console.broadcast({
        "type": "photo_override", "task_id": task_id, "photo_id": photo.id, "admin_override": approved,
    })
    return {"id": photo.id, "admin_override": photo.admin_override}


@app.post("/tasks/{task_id}/checkin")
async def submit_checkin_photo(
    task_id: str,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Worker submits a photo of the pinned location, for location_mode='photo_checkin'.
    Task stays 'assigned' until the manager approves it via /tasks/{id}/checkin/approve."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    fname = f"{task_id}_checkin_{datetime.datetime.utcnow().timestamp()}_{photo.filename}"
    path = os.path.join(UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        shutil.copyfileobj(photo.file, f)
    task.checkin_photo_url = f"/uploads/{fname}"
    task.checkin_approved = None  # pending review
    db.commit()
    db.refresh(task)

    await manager_console.broadcast({
        "type": "checkin_submitted", "task_id": task.id,
        "checkin_photo_url": task.checkin_photo_url,
    })
    return {"id": task.id, "checkin_photo_url": task.checkin_photo_url}


@app.post("/tasks/{task_id}/checkin/approve")
async def approve_checkin(
    task_id: str,
    approved: bool = Form(...),
    db: Session = Depends(get_db),
):
    """Manager approves or rejects a worker's location check-in photo."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    task.checkin_approved = approved
    db.commit()
    db.refresh(task)

    await manager_console.broadcast({
        "type": "checkin_reviewed", "task_id": task.id, "checkin_approved": approved,
    })
    return {"id": task.id, "checkin_approved": approved}


@app.post("/tasks/{task_id}/reply")
async def worker_reply(
    task_id: str,
    original_text: str = Form(...),      # what the worker actually said, in their language
    original_lang: str = Form(...),
    translated_text: str = Form(...),    # ML Kit's on-device translation to the manager's language
    translated_lang: str = Form(...),
    db: Session = Depends(get_db),
):
    """Worker speaks a reply, phone runs speech-to-text, ML Kit translates it
    back to the manager's language on-device, and this just delivers the
    already-translated text to the console. Server does no translation work
    for app workers - only WhatsApp workers need that server-side."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    msg = Message(
        worker_id=task.worker_id, direction="from_worker",
        original_text=original_text, original_lang=original_lang,
        translated_text=translated_text, translated_lang=translated_lang,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    await manager_console.broadcast({
        "type": "worker_reply", "task_id": task.id, "worker_id": task.worker_id,
        "text": translated_text, "original_text": original_text,
    })
    return {"id": msg.id, "translated_text": translated_text}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/apk/upload")
async def upload_apk(
    request: Request,
    version_code: int = Form(...),
    version_name: str = Form(...),
    notes: str = Form(""),
    apk: UploadFile = File(...),
):
    """Called by CI after a successful build to publish the newest APK.
    Requires a shared secret (X-Deploy-Secret header) matching
    APK_UPLOAD_SECRET on this server - NOT the same thing as a GitHub
    token, so nothing sensitive to the repo itself is ever exposed here
    or embedded in the distributed app."""
    if not APK_UPLOAD_SECRET or request.headers.get("X-Deploy-Secret") != APK_UPLOAD_SECRET:
        raise HTTPException(403, "Missing or invalid deploy secret")
    if not apk.filename.endswith(".apk"):
        raise HTTPException(400, "Expected a .apk file")

    contents = await apk.read()
    with open(os.path.join(APK_DIR, "latest.apk"), "wb") as f:
        f.write(contents)

    meta = {
        "version_code": version_code,
        "version_name": version_name,
        "notes": notes,
        "uploaded_at": datetime.datetime.utcnow().isoformat() + "Z",
        "url": "/apk/latest.apk",
    }
    with open(os.path.join(APK_DIR, "latest.json"), "w") as f:
        json.dump(meta, f)

    return {"status": "ok", **meta}


# Mounted after the POST route above, not before: a StaticFiles mount only
# handles GET/HEAD and matches by path prefix regardless of registration
# order relative to routes defined "later" in the file - if this were
# mounted up top like /uploads is, it would shadow POST /apk/upload with
# a 405 before the real route ever got a chance to run.
app.mount("/apk", StaticFiles(directory=APK_DIR), name="apk")


# Manager console (static frontend). Mounted last so it never shadows API routes above.
os.makedirs(os.path.join(STATIC_DIR, "console"), exist_ok=True)
app.mount("/console", StaticFiles(directory=os.path.join(STATIC_DIR, "console"), html=True), name="console")
