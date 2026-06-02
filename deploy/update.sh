#!/usr/bin/env sh
# Обновление staging на сервере: git pull -> precheck -> restart -> smoke
set -eu

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
sudo systemctl --no-pager --full status "$SERVICE_NAME" | grep -E "Active:|Main PID:" || true

echo "==> Wait for local health"
attempt=0
while [ "$attempt" -lt 20 ]; do
  if curl -fsS "$BASE_URL/api/v1/health" >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 1
done

echo "==> Smoke checks"
curl -fsS "$BASE_URL/api/v1/health" | head -c 300
echo
curl -fsS "${PUBLIC_BASE_URL:-https://flexity.asia}/api/v1/health" | head -c 300
echo
