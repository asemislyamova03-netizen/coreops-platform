#!/usr/bin/env bash
# Обновление staging на сервере: git pull -> precheck -> restart -> smoke
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
SERVICE_NAME="${SERVICE_NAME:-coreops}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8005}"
VENV_PYTHON="${VENV_PYTHON:-/opt/flexity/envs/coreops/bin/python}"

echo "==> Pull latest changes"
cd "$ROOT_DIR"
git pull --ff-only

echo "==> Run pre-deploy checks"
BASE_URL="$BASE_URL" VENV_PYTHON="$VENV_PYTHON" "$ROOT_DIR/deploy/predeploy-check.sh"

echo "==> Restart service: $SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl --no-pager --full status "$SERVICE_NAME" | rg -n "Active:|Main PID:" || true

echo "==> Smoke checks"
curl -fsS "$BASE_URL/api/v1/health" | head -c 300
echo
curl -fsSI "${PUBLIC_BASE_URL:-https://flexity.asia}/api/v1/health" | head -n 5
