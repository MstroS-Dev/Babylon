#!/usr/bin/env bash
# Site Comms server install script — Ubuntu Server.
# Paste this whole block into an SSH session on your fresh server.
set -e

REPO_URL="https://github.com/MstroS-Dev/Babylon.git"
APP_DIR="/opt/site-comms"

echo "== Installing system packages =="
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

echo "== Cloning repo =="
sudo rm -rf "$APP_DIR"
sudo git clone "$REPO_URL" "$APP_DIR"
cd "$APP_DIR/server"

echo "== Setting up virtual environment =="
sudo python3 -m venv venv
sudo ./venv/bin/pip install --upgrade pip
sudo ./venv/bin/pip install -r requirements.txt

echo "== Configuring environment =="
if [ ! -f /etc/site-comms.env ]; then
  read -p "Enter your ANTHROPIC_API_KEY: " ANTHROPIC_KEY
  echo "ANTHROPIC_API_KEY=$ANTHROPIC_KEY" | sudo tee /etc/site-comms.env > /dev/null
  echo "Add TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_FROM to /etc/site-comms.env later, once you have WhatsApp set up."
fi

echo "== Creating systemd service =="
sudo tee /etc/systemd/system/site-comms.service > /dev/null <<EOF
[Unit]
Description=Site Comms Server
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR/server
EnvironmentFile=/etc/site-comms.env
ExecStart=$APP_DIR/server/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable site-comms
sudo systemctl restart site-comms

echo "== Done =="
echo "Server should be live on port 8000. Check status with:"
echo "  sudo systemctl status site-comms"
echo "View logs with:"
echo "  sudo journalctl -u site-comms -f"
echo ""
echo "To update after pushing new code to GitHub, re-run this script,"
echo "or just: cd $APP_DIR && sudo git pull && sudo systemctl restart site-comms"
