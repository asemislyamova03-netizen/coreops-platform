# Деплой Flexity / CoreOps на сервер (первый раз)

Требования на сервере: **Docker** и **Docker Compose v2**, открытый порт **8000** (или за reverse proxy).

## 1. Клонирование

```bash
sudo mkdir -p /opt/flexity
sudo chown "$USER:$USER" /opt/flexity
cd /opt/flexity
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> .
# или: git clone <URL> flexity && cd flexity
```

## 2. Переменные окружения

```bash
cd /opt/flexity/backend
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

```bash
cd /opt/flexity/backend
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api
```

Проверка: `curl -s http://127.0.0.1:8000/api/v1/health`

## 4. Обновление после `git push`

```bash
cd /opt/flexity
git pull
cd backend
docker compose -f docker-compose.prod.yml up -d --build
```

## 5. Nginx (опционально)

Проксируйте `https://api.example.com` → `127.0.0.1:8000`, включите TLS (certbot).

## 6. Первый пользователь

Пока БД пустая, один раз:

```bash
curl -X POST https://api.example.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"...","full_name":"Owner","company_name":"My Firm","company_slug":"my-firm"}'
```

После появления пользователей `/auth/register` для provider отключается.
