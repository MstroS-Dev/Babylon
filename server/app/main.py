import os
import shutil
import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .db import init_db, get_db
from .models import Worker, Task, Message
from .translate import translate_text
from .claude_review import review_task
from .whatsapp import send_whatsapp_message

MANAGER_LANGUAGE = "he"  # your friend's default language, change as needed

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Site Comms Server")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

init_db()


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


# ---------- Tasks ----------

@app.post("/tasks")
async def create_task(
    worker_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    detailed_description: Optional[str] = Form(None),
    manager_lang: str = Form(MANAGER_LANGUAGE),
    db: Session = Depends(get_db),
):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(404, "Worker not found")

    task = Task(worker_id=worker_id, title=title, description=description,
                detailed_description=detailed_description, status="assigned")
    db.add(task)
    db.commit()
    db.refresh(task)

    # App users translate on-device (ML Kit) - server just sends original text + a push notification.
    # WhatsApp users need server-side translation before sending.
    if worker.channel == "whatsapp":
        translated = translate_text(f"{title}\n{description}", manager_lang, worker.language)
        send_whatsapp_message(worker.phone, translated)
        db.add(Message(worker_id=worker.id, direction="to_worker",
                        original_text=f"{title}\n{description}", original_lang=manager_lang,
                        translated_text=translated, translated_lang=worker.language))
        db.commit()
    else:
        # TODO: push notification to app via device_token (FCM), app translates locally.
        pass

    await manager_console.broadcast({"type": "task_created", "task_id": task.id, "worker_id": worker.id})
    return {"id": task.id, "status": task.status}


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
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "in_progress_at": t.in_progress_at.isoformat() if t.in_progress_at else None,
            "done_at": t.done_at.isoformat() if t.done_at else None,
        }
        for t in tasks
    ]


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
    for photo in photos:
        fname = f"{task_id}_{stage}_{datetime.datetime.utcnow().timestamp()}_{photo.filename}"
        path = os.path.join(UPLOAD_DIR, fname)
        with open(path, "wb") as f:
            shutil.copyfileobj(photo.file, f)
        saved_urls.append(f"/uploads/{fname}")

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
        "claude_review": task.claude_review,
    })
    return {"id": task.id, "status": task.status, "claude_review": task.claude_review}


@app.get("/health")
def health():
    return {"status": "ok"}
