#!/usr/bin/env sh
# Проверка готовности CoreOps к деплою на сервере.
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_PYTHON="${VENV_PYTHON:-/opt/flexity/envs/coreops/bin/python}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8005}"

if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo "ERROR: missing $BACKEND_DIR/.env"
  exit 1
fi

for var_name in DATABASE_URL SECRET_KEY APP_ENV; do
  if ! grep -Eq "^${var_name}=" "$BACKEND_DIR/.env"; then
    echo "ERROR: $var_name is missing in backend/.env"
    exit 1
  fi
done

if grep -Eq "^DEBUG=true" "$BACKEND_DIR/.env"; then
  echo "WARN: DEBUG=true in backend/.env (recommended false on server)"
fi

if grep -Eq "^SEED_ON_STARTUP=true" "$BACKEND_DIR/.env"; then
  echo "WARN: SEED_ON_STARTUP=true in backend/.env (recommended false on server)"
fi

echo "Running DB migrations dry check (upgrade head)..."
cd "$BACKEND_DIR"
"$VENV_PYTHON" -m alembic.config upgrade head

echo "Checking health endpoint: $BASE_URL/api/v1/health"
curl -fsS "$BASE_URL/api/v1/health" >/dev/null

echo "Pre-deploy checks passed."
