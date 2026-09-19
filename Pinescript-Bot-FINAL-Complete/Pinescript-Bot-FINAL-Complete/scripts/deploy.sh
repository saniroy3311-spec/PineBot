#!/usr/bin/env bash
set -euo pipefail

: "${VPS_IP:?Set VPS_IP, e.g. VPS_IP=203.0.113.10 bash scripts/deploy.sh}"
VPS_USER="${VPS_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/pinescript-bot}"
SERVICE_NAME="pinescript_bot"

echo "Deploying Pinescript Bot to ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}"
ssh "${VPS_USER}@${VPS_IP}" "apt-get update -qq && apt-get install -y python3 python3-venv python3-pip rsync"
ssh "${VPS_USER}@${VPS_IP}" "mkdir -p '${REMOTE_DIR}'"
rsync -avz --delete \
  --exclude='.git' --exclude='.env' --exclude='.venv' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='data/*.db' --exclude='logs/*' \
  ./ "${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/"
ssh "${VPS_USER}@${VPS_IP}" "cd '${REMOTE_DIR}' && python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt"
ssh "${VPS_USER}@${VPS_IP}" "[ -f '${REMOTE_DIR}/.env' ] || cp '${REMOTE_DIR}/.env.example' '${REMOTE_DIR}/.env'"
ssh "${VPS_USER}@${VPS_IP}" "cp '${REMOTE_DIR}/systemd/pinescript_bot.service' /etc/systemd/system/pinescript_bot.service && systemctl daemon-reload && systemctl enable pinescript_bot"

echo "Deployment copied. Edit ${REMOTE_DIR}/.env, run validate_setup.py, then start with: systemctl start ${SERVICE_NAME}"
