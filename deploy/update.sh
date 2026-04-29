#!/usr/bin/env bash
#
# Pull latest code, reinstall deps, restart timers.
# Run as root or with sudo.
#
set -euo pipefail

INSTALL_DIR="/opt/pharma-intelligence"
DEPLOY_USER="pharma"

echo "=== Pharma Intelligence — Update ==="

cd "$INSTALL_DIR"

echo "[1/4] Pulling latest code..."
sudo -u "$DEPLOY_USER" git pull --ff-only

echo "[2/4] Updating Python dependencies..."
sudo -u "$DEPLOY_USER" "${INSTALL_DIR}/venv/bin/pip" install -r requirements.txt -q

echo "[3/4] Updating systemd units..."
cp "${INSTALL_DIR}/deploy/systemd/"*.service /etc/systemd/system/
cp "${INSTALL_DIR}/deploy/systemd/"*.timer /etc/systemd/system/
cp "${INSTALL_DIR}/deploy/logrotate.d/pharma-scrapers" /etc/logrotate.d/pharma-scrapers
systemctl daemon-reload

echo "[4/4] Restarting timers..."
systemctl restart pharma-full-scrape.timer
systemctl restart pharma-daily-tracker.timer

echo ""
echo "Done. Timer status:"
systemctl list-timers pharma-* --no-pager
