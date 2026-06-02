#!/usr/bin/env bash
# Проверка готовности CoreOps к деплою на сервере.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_PYTHON="${VENV_PYTHON:-/opt/flexity/envs/coreops/bin/python}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8005}"

if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  echo "ERROR: missing $BACKEND_DIR/.env"
  exit 1
fi

required_vars=(
  "DATABASE_URL"
  "SECRET_KEY"
  "APP_ENV"
)

for var_name in "${required_vars[@]}"; do
  if ! rg -n "^${var_name}=" "$BACKEND_DIR/.env" >/dev/null; then
    echo "ERROR: $var_name is missing in backend/.env"
    exit 1
  fi
done

if rg -n "^DEBUG=true" "$BACKEND_DIR/.env" >/dev/null; then
  echo "WARN: DEBUG=true in backend/.env (recommended false on server)"
fi

if rg -n "^SEED_ON_STARTUP=true" "$BACKEND_DIR/.env" >/dev/null; then
  echo "WARN: SEED_ON_STARTUP=true in backend/.env (recommended false on server)"
fi

echo "Running DB migrations dry check (upgrade head)..."
cd "$BACKEND_DIR"
"$VENV_PYTHON" -m alembic upgrade head

echo "Checking health endpoint: $BASE_URL/api/v1/health"
curl -fsS "$BASE_URL/api/v1/health" >/dev/null

echo "Pre-deploy checks passed."
