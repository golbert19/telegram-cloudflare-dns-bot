#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/golbert19/telegram-cloudflare-dns-bot.git"
APP_DIR="/opt/telegram-cloudflare-dns-bot"
SERVICE_USER="dnsbot"

sudo apt update
sudo apt install -y git python3 python3-pip python3-venv

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  sudo useradd --system --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

if [ ! -d "$APP_DIR/.git" ]; then
  sudo git clone "$REPO" "$APP_DIR"
else
  cd "$APP_DIR"
  sudo -u "$SERVICE_USER" git pull
fi

sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"
cd "$APP_DIR"

if [ ! -d venv ]; then
  sudo -u "$SERVICE_USER" python3 -m venv venv
fi

sudo -u "$SERVICE_USER" ./venv/bin/pip install --upgrade pip
sudo -u "$SERVICE_USER" ./venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
  sudo -u "$SERVICE_USER" cp .env.example .env
  sudo chmod 600 .env
  echo
  echo "Se creó $APP_DIR/.env"
  echo "Edítalo con: sudo nano $APP_DIR/.env"
fi

sudo cp deploy/dnsbot.service.example /etc/systemd/system/dnsbot.service
sudo systemctl daemon-reload

echo
printf '%s\n' \
  "Proyecto instalado." \
  "1) Completa: sudo nano $APP_DIR/.env" \
  "2) Inicia:   sudo systemctl enable --now dnsbot" \
  "3) Estado:   sudo systemctl status dnsbot" \
  "4) Logs:     sudo journalctl -u dnsbot -f"


# Alinear dominio e IP del despliegue
if grep -q '^BASE_DOMAIN=' "$APP_DIR/.env"; then
    sed -i 's/^BASE_DOMAIN=.*/BASE_DOMAIN=golbertvps.net.pe/' "$APP_DIR/.env"
else
    echo 'BASE_DOMAIN=golbertvps.net.pe' >> "$APP_DIR/.env"
fi

if grep -q '^VPS_IP=' "$APP_DIR/.env"; then
    sed -i 's/^VPS_IP=.*/VPS_IP=45.41.207.172/' "$APP_DIR/.env"
else
    echo 'VPS_IP=45.41.207.172' >> "$APP_DIR/.env"
fi


if grep -q '^TELEGRAM_ADMIN_ID=' "$APP_DIR/.env"; then
    sed -i 's/^TELEGRAM_ADMIN_ID=.*/TELEGRAM_ADMIN_ID=8823167645/' "$APP_DIR/.env"
else
    echo 'TELEGRAM_ADMIN_ID=8823167645' >> "$APP_DIR/.env"
fi
