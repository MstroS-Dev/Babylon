"""
Push notifications to app workers via Firebase Cloud Messaging (FCM).

Right now the app has no way to know a new task exists until the worker
manually pulls to refresh. This sends a silent/data push so the app can
fetch immediately.

This is a stub until a Firebase project exists — same pattern as
whatsapp.py. To go live:

1. Go to https://console.firebase.google.com, create a project (free).
2. Project settings -> Service accounts -> Generate new private key.
   This downloads a JSON file - copy its contents into the
   FIREBASE_SERVICE_ACCOUNT_JSON environment variable on the server
   (the whole JSON, as a single-line string).
3. Project settings -> General -> Add app -> Android. Use package name
   com.babylon.site. Download the resulting google-services.json and
   drop it into android/app/google-services.json in the repo.
4. Tell me once both are in place and I'll wire up the Android SDK side
   (currently commented out of app/build.gradle.kts so CI builds don't
   break without the json file present).

Until then, this just logs what *would* have been sent, exactly like
WhatsApp's dev mode - task creation and everything else keeps working.
"""
import os
import json

FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

_access_token_cache = {"token": None, "expires_at": 0}


def _get_access_token():
    import time
    import urllib.request

    if _access_token_cache["token"] and time.time() < _access_token_cache["expires_at"] - 60:
        return _access_token_cache["token"]

    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    info = json.loads(FIREBASE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )
    creds.refresh(Request())
    _access_token_cache["token"] = creds.token
    _access_token_cache["expires_at"] = time.time() + 3500
    return creds.token


def send_task_push(device_token: str, task_id: str, title: str) -> dict:
    """Notify a worker's phone that a new task is waiting. Data-only payload -
    the app decides how to surface it (it already has the real, translated
    text once it fetches /tasks, so we don't put message content in the push
    itself)."""
    if not device_token:
        return {"status": "skipped", "reason": "no device token on file"}

    if not FIREBASE_SERVICE_ACCOUNT_JSON:
        print(f"[push:DEV MODE] to={device_token[:12]}... task={task_id} title={title!r}")
        return {"status": "dev_mode"}

    import urllib.request

    info = json.loads(FIREBASE_SERVICE_ACCOUNT_JSON)
    project_id = info["project_id"]
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

    payload = {
        "message": {
            "token": device_token,
            "data": {"type": "new_task", "task_id": task_id, "title": title},
            "android": {"priority": "high"},
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {_get_access_token()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": "sent", "response": resp.read().decode()}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
