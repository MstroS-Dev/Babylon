#!/usr/bin/env bash
# One-time SSL setup for an already-running site-comms server.
# Paste this whole block into an SSH session on the server.
#
# What this does:
#   1. Installs nginx + certbot (free, from Ubuntu's package repos / EFF's
#      certbot repo - no paid service involved).
#   2. Sets nginx up as a reverse proxy in front of uvicorn (which keeps
#      running on 127.0.0.1:8000, now only reachable through nginx).
#   3. Gets a free Let's Encrypt certificate for this server's EC2 hostname
#      and points nginx at it - certbot also sets up automatic renewal
#      (Let's Encrypt certs expire every 90 days; certbot's systemd timer
#      renews them automatically, nothing to do afterward).
#
# Prerequisite you need to check yourself first: your EC2 instance's
# Security Group must allow inbound traffic on ports 80 and 443 (not just
# 8000). This script can't check or change that - it's an AWS console
# setting, not something on the box itself.
set -e

DOMAIN="site-comms.16.170.108.223.sslip.io"
APP_DIR="/opt/site-comms"

echo "== Installing nginx + certbot =="
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

echo "== Ensuring nginx can handle our (longer than default) hostname =="
if ! grep -q "server_names_hash_bucket_size" /etc/nginx/nginx.conf; then
  sudo sed -i '/http {/a \\tserver_names_hash_bucket_size 64;' /etc/nginx/nginx.conf
fi

echo "== Installing reverse proxy config =="
sudo cp "$APP_DIR/nginx-site-comms.conf" /etc/nginx/sites-available/site-comms
sudo ln -sf /etc/nginx/sites-available/site-comms /etc/nginx/sites-enabled/site-comms
# Note: NOT removing sites-enabled/default or any other site here - this
# server also hosts other, unrelated sites (e.g. etay-training), and this
# script has no business touching those.
sudo nginx -t
sudo systemctl reload nginx

echo "== Requesting free Let's Encrypt certificate =="
echo "You'll be asked for an email (for renewal/expiry notices) and to"
echo "agree to Let's Encrypt's terms. When asked whether to redirect HTTP"
echo "to HTTPS, choose yes (option 2) - recommended."
sudo certbot --nginx -d "$DOMAIN"

echo "== Updating uvicorn to trust nginx's forwarded headers =="
sudo sed -i \
  's|ExecStart=.*uvicorn.*|ExecStart='"$APP_DIR"'/server/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1|' \
  /etc/systemd/system/site-comms.service
sudo systemctl daemon-reload
sudo systemctl restart site-comms

echo "== Done =="
echo "Your server should now be reachable at:"
echo "  https://$DOMAIN"
echo ""
echo "Certbot installed a systemd timer for automatic renewal - check it with:"
echo "  systemctl list-timers | grep certbot"
echo ""
echo "IMPORTANT - things that still need updating after this:"
echo "  1. android/app/.../data/ApiConfig.kt - change BASE_URL from http:// to https://"
echo "  2. The APK_SERVER_URL GitHub Actions repo variable - same http:// to https:// change"
echo "  3. Port 8000 is no longer exposed directly (uvicorn now binds 127.0.0.1 only,"
echo "     reachable only through nginx on 443) - that's intentional, not a bug."
