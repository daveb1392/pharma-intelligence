#!/usr/bin/env bash
#
# One-shot bootstrap for a fresh Hetzner VPS.
# Run as root on Ubuntu 24.04 LTS.
#
# Usage:
#   curl -sSL <raw-github-url>/deploy/bootstrap.sh | bash
#   — or —
#   git clone <repo> /opt/pharma-intelligence && cd /opt/pharma-intelligence && bash deploy/bootstrap.sh
#
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/daveb1392/pharma-intelligence.git}"
INSTALL_DIR="/opt/pharma-intelligence"
DEPLOY_USER="pharma"
LOG_DIR="/var/log/pharma"
PYTHON_VERSION="3.11"  # minimum; will use whatever 3.11+ is available

echo "=== Pharma Intelligence — Hetzner Bootstrap ==="

# ── 0. Must be root ────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Run this script as root."
    exit 1
fi

# ── 1. System packages ────────────────────────────────────────────
echo "[1/8] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    git curl wget unzip \
    python3 python3-venv python3-pip python3-dev \
    build-essential libffi-dev libssl-dev \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2t64 libxshmfence1 \
    ufw logrotate

# ── 2. Timezone ────────────────────────────────────────────────────
echo "[2/8] Setting timezone to America/Asuncion..."
timedatectl set-timezone America/Asuncion

# ── 3. Deploy user ─────────────────────────────────────────────────
echo "[3/8] Creating deploy user '${DEPLOY_USER}'..."
if ! id "$DEPLOY_USER" &>/dev/null; then
    useradd -r -m -s /bin/bash "$DEPLOY_USER"
fi

# ── 4. Clone or update repo ───────────────────────────────────────
echo "[4/8] Setting up project at ${INSTALL_DIR}..."
if [[ -d "${INSTALL_DIR}/.git" ]]; then
    echo "  Repo already exists — pulling latest..."
    cd "$INSTALL_DIR"
    git pull --ff-only
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "$INSTALL_DIR"

# ── 5. Python venv + deps ─────────────────────────────────────────
echo "[5/8] Creating Python venv and installing dependencies..."
sudo -u "$DEPLOY_USER" python3 -m venv "${INSTALL_DIR}/venv"
sudo -u "$DEPLOY_USER" "${INSTALL_DIR}/venv/bin/pip" install --upgrade pip
sudo -u "$DEPLOY_USER" "${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

# ── 6. Playwright + Chromium ──────────────────────────────────────
echo "[6/8] Installing Playwright Chromium..."
sudo -u "$DEPLOY_USER" "${INSTALL_DIR}/venv/bin/playwright" install --with-deps chromium

# ── 7. Logging + logrotate ─────────────────────────────────────────
echo "[7/8] Setting up logging..."
mkdir -p "$LOG_DIR"
chown "${DEPLOY_USER}:${DEPLOY_USER}" "$LOG_DIR"
cp "${INSTALL_DIR}/deploy/logrotate.d/pharma-scrapers" /etc/logrotate.d/pharma-scrapers

# ── 8. systemd units ──────────────────────────────────────────────
echo "[8/8] Installing systemd services and timers..."
cp "${INSTALL_DIR}/deploy/systemd/"*.service /etc/systemd/system/
cp "${INSTALL_DIR}/deploy/systemd/"*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable pharma-full-scrape.timer
systemctl enable pharma-daily-tracker.timer
systemctl start pharma-full-scrape.timer
systemctl start pharma-daily-tracker.timer

# ── Firewall ───────────────────────────────────────────────────────
echo "Configuring firewall (SSH only)..."
ufw allow OpenSSH
ufw --force enable

# ── Done ───────────────────────────────────────────────────────────
echo ""
echo "=== Bootstrap complete ==="
echo ""
echo "NEXT STEPS:"
echo "  1. Copy your .env file:"
echo "     cp ${INSTALL_DIR}/deploy/.env.example ${INSTALL_DIR}/.env"
echo "     nano ${INSTALL_DIR}/.env   # fill in real Supabase credentials"
echo "     chmod 600 ${INSTALL_DIR}/.env"
echo "     chown ${DEPLOY_USER}:${DEPLOY_USER} ${INSTALL_DIR}/.env"
echo ""
echo "  2. Test a scraper manually:"
echo "     sudo -u ${DEPLOY_USER} ${INSTALL_DIR}/venv/bin/python -m scrapers.farmacia_catedral phase1"
echo ""
echo "  3. Check timer status:"
echo "     systemctl list-timers pharma-*"
echo ""
echo "  4. Check health:"
echo "     bash ${INSTALL_DIR}/deploy/healthcheck.sh --verbose"
echo ""
