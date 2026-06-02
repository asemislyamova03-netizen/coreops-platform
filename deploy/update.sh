#!/usr/bin/env bash
# Запуск на сервере из корня клона: ./deploy/update.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
curl -sf "http://127.0.0.1:${API_PORT:-8000}/api/v1/health" | head -c 200
echo
