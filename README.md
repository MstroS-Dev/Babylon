# Babylon — Site Comms

A translation and task-management app for construction site managers with
multilingual crews. Manager sends a task in his language; each worker gets
it translated and read aloud in theirs, and confirms completion with
before/after photos.

## Structure

- **`server/`** — Python (FastAPI) backend. Worker registration, task
  creation/tracking, WhatsApp fallback channel, Claude-based photo review.
  See `server/README.md` for full details.
- **`android/`** — Android app (Kotlin). Registration, task list, on-device
  translation via ML Kit, text-to-speech, before/after photo capture.
- **`.github/workflows/build-apk.yml`** — builds a debug APK automatically
  on every push to `android/`. Download it from the Actions tab → latest
  run → Artifacts.
- **`install.sh`** — one-paste SSH install script for a fresh Ubuntu server.
  Sets up the server as a systemd service.

## Getting the server running

SSH into your Ubuntu server and run:

```bash
curl -sSL https://raw.githubusercontent.com/MstroS-Dev/Babylon/main/install.sh | bash
```

(Or copy-paste the contents of `install.sh` directly if you'd rather review it first.)

It'll ask for your Anthropic API key, then set the server up as a
systemd service listening on port 8000.

## Getting the APK

Push any change to `android/`, then check the **Actions** tab on GitHub —
the workflow builds `app-debug.apk` automatically. Download it from the
run's Artifacts section and side-load it onto worker phones.

Before building, update `BASE_URL` in
`android/app/src/main/java/com/babylon/site/data/ApiConfig.kt` to point at
your actual server's IP or domain.

## What's built vs. what's next

Built and tested: worker registration, task CRUD, status flow
(assigned → in_progress → done), photo upload, Claude photo review,
on-device translation, TTS.

Still to wire up: push notifications to the app (FCM), the WhatsApp
incoming-message webhook, and auth on the manager endpoints. See
`server/README.md` for the details.
