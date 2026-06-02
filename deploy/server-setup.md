# Деплой Flexity / CoreOps на сервер (первый раз)

**Staging:** Lightsail (`ssh flexity`), **flexity.asia**.  
Trailers и Consult **пока остаются** — CoreOps только на `/api/` и `/docs`, порт **8005**.  
Схема nginx: [flexity-asia-nginx.md](flexity-asia-nginx.md). Production позже — **flexity.kz**.

| Что | Значение |
|-----|----------|
| Код | `/opt/flexity/coreops` |
| API (внутри) | `127.0.0.1:8005` |
| Снаружи | `https://flexity.asia/api/v1/...`, `/docs` |

venv + systemd + локальный PostgreSQL (Docker опционален).

## 1. Клонирование

```bash
sudo mkdir -p /opt/flexity/coreops
sudo chown "$USER:$USER" /opt/flexity/coreops
cd /opt/flexity/coreops
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> .
```

## 2. Переменные окружения

```bash
cd /opt/flexity/coreops/backend
cp .env.example .env
nano .env
```

Обязательно измените:

- `SECRET_KEY` — случайная строка, например: `openssl rand -hex 32`
- `POSTGRES_PASSWORD` — в `.env` для compose (см. ниже)
- `DEBUG=false`, `APP_ENV=production`, `SEED_ON_STARTUP=false` на проде

Добавьте в `backend/.env` (для `docker-compose.prod.yml`):

```env
POSTGRES_USER=coreops
POSTGRES_PASSWORD=<сильный_пароль>
POSTGRES_DB=coreops
API_PORT=8000
```

`DATABASE_URL` в compose подставляется автоматически из этих переменных.

## 3. Запуск

**Вариант A — как на сервере сейчас (venv + systemd, рекомендуется):**

```bash
python3 -m venv /opt/flexity/envs/coreops
/opt/flexity/envs/coreops/bin/pip install -e /opt/flexity/coreops/backend
cd /opt/flexity/coreops/backend && /opt/flexity/envs/coreops/bin/alembic upgrade head
# systemd unit → uvicorn на 127.0.0.1:8005 (см. flexity-asia-nginx.md)
```

Установка готового unit-файла из репозитория:

```bash
cd /opt/flexity/coreops
sudo cp deploy/coreops.service /etc/systemd/system/coreops.service
sudo systemctl daemon-reload
sudo systemctl enable --now coreops
sudo systemctl status coreops --no-pager
```

Логи:

```bash
sudo journalctl -u coreops -f
```

Установка готового unit-файла из репозитория:

```bash
cd /opt/flexity/coreops
sudo cp deploy/coreops.service /etc/systemd/system/coreops.service
sudo systemctl daemon-reload
sudo systemctl enable --now coreops
sudo systemctl status coreops --no-pager
```

Логи:

```bash
sudo journalctl -u coreops -f
```

**Вариант B — Docker** (если установлен):

```bash
cd /opt/flexity/coreops/backend
docker compose -f docker-compose.prod.yml up -d --build
```

Проверка локально: `curl -s http://127.0.0.1:8005/api/v1/health`  
Через сайт (после nginx): `curl -s https://flexity.asia/api/v1/health`

## 3.1 Pre-deploy проверка (рекомендуется)

Перед перезапуском сервиса:

```bash
cd /opt/flexity/coreops
chmod +x deploy/predeploy-check.sh
BASE_URL=http://127.0.0.1:8005 VENV_PYTHON=/opt/flexity/envs/coreops/bin/python ./deploy/predeploy-check.sh
```

Скрипт проверяет:

- наличие `backend/.env`;
- обязательные env (`DATABASE_URL`, `SECRET_KEY`, `APP_ENV`);
- предупреждает о `DEBUG=true` и `SEED_ON_STARTUP=true`;
- применяет миграции `alembic upgrade head`;
- проверяет health endpoint.

## 4. Nginx на flexity.asia

В `/etc/nginx/sites-enabled/flexity.asia.conf` добавить `location ^~ /api/` **перед** `location /` → 8002.  
Готовый фрагмент: [flexity-asia-nginx.md](flexity-asia-nginx.md).

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 5. Обновление после `git push`

```bash
cd /opt/flexity/coreops && git pull
BASE_URL=http://127.0.0.1:8005 VENV_PYTHON=/opt/flexity/envs/coreops/bin/python ./deploy/predeploy-check.sh
cd backend && /opt/flexity/envs/coreops/bin/alembic upgrade head
sudo systemctl restart coreops
```

или одной командой:

```bash
cd /opt/flexity/coreops
chmod +x deploy/*.sh
./deploy/update.sh
```

## 6. Первый пользователь

Пока БД пустая, один раз:

```bash
curl -X POST https://api.example.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"...","full_name":"Owner","company_name":"My Firm","company_slug":"my-firm"}'
```

После появления пользователей `/auth/register` для provider отключается.
