#!/usr/bin/env bash
# Site Comms server install script — Ubuntu Server.
# Paste this whole block into an SSH session on your fresh server.
set -e

REPO_URL="https://github.com/MstroS-Dev/Babylon.git"
APP_DIR="/opt/site-comms"
DOMAIN="site-comms.16.170.108.223.sslip.io"

echo "== Installing system packages =="
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx

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
# Bound to 127.0.0.1, not 0.0.0.0 - nginx (set up below) is the only thing
# that should be reachable from outside; it terminates TLS and forwards to
# uvicorn locally. --proxy-headers/--forwarded-allow-ips lets uvicorn trust
# nginx's X-Forwarded-* headers (client IP, https scheme) instead of
# treating every request as if it came from nginx itself.
sudo tee /etc/systemd/system/site-comms.service > /dev/null <<EOF
[Unit]
Description=Site Comms Server
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR/server
EnvironmentFile=/etc/site-comms.env
ExecStart=$APP_DIR/server/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable site-comms
sudo systemctl restart site-comms

echo "== Setting up nginx reverse proxy =="
if ! grep -q "server_names_hash_bucket_size" /etc/nginx/nginx.conf; then
  sudo sed -i '/http {/a \\tserver_names_hash_bucket_size 64;' /etc/nginx/nginx.conf
fi
sudo cp "$APP_DIR/nginx-site-comms.conf" /etc/nginx/sites-available/site-comms
sudo ln -sf /etc/nginx/sites-available/site-comms /etc/nginx/sites-enabled/site-comms
sudo nginx -t
sudo systemctl reload nginx

echo "== Requesting free Let's Encrypt certificate =="
echo "Make sure your EC2 Security Group allows inbound 80 and 443 before this step."
echo "You'll be asked for an email and to agree to Let's Encrypt's terms."
sudo certbot --nginx -d "$DOMAIN"

echo "== Done =="
echo "Server should be live at https://$DOMAIN"
echo "Check status with:"
echo "  sudo systemctl status site-comms"
echo "View logs with:"
echo "  sudo journalctl -u site-comms -f"
echo ""
echo "To update after pushing new code to GitHub, re-run this script,"
echo "or just: cd $APP_DIR && sudo git pull && sudo systemctl restart site-comms"
