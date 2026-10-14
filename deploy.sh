#!/usr/bin/env bash
# One-command update for the live server:  cd /opt/site-comms && ./deploy.sh
# Pulls the latest code, installs any new Python dependencies, restarts the service.
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
sudo git pull --ff-only
sudo "$APP_DIR/server/venv/bin/pip" install -q -r "$APP_DIR/server/requirements.txt"
sudo systemctl restart site-comms
sleep 2
sudo systemctl is-active site-comms
curl -fsS http://127.0.0.1:8000/health && echo
echo "Deployed. Hard-refresh the console (Ctrl+Shift+R)."
