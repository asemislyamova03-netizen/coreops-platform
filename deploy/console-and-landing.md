# Platform Console и Landing — deploy (документация)

**Статус:** документация only. Выполнение ssh/scp/nginx reload — только с отдельным approval.

**Связанные документы:**

- [flexity-asia-nginx.md](flexity-asia-nginx.md) — CoreOps `/api/` на порту 8005
- [server-setup.md](server-setup.md) — первичная настройка сервера
- План: `docs/ai/plans/2026-06-10-console-and-landing-deploy-prep-plan.md`

---

## Целевая схема URL

| URL | Сервис | Источник на сервере |
|-----|--------|---------------------|
| `https://www.flexity.asia/` | Публичный лендинг (статика) | `landing/www/` из репозитория → `/var/www/flexity-landing/` |
| `https://flexity.asia/api/` | Flexity FastAPI (CoreOps) | proxy → `127.0.0.1:8005` |
| `https://flexity.asia/console/` | Platform Console SPA | `platform-console/dist/` |
| `https://flexity.asia/console/login` | Login (deep link) | SPA fallback → `index.html` |
| `https://flexity.asia/console/tenants` | Tenants (deep link) | SPA fallback → `index.html` |
| `https://flexity.asia/` | **Legacy Consult** | proxy → `127.0.0.1:8002` — **не ломать** без отдельного product-решения |
| `https://flexity.asia/trailers/` | Legacy Trailers | proxy → `127.0.0.1:8003` — не трогать |
| `https://admin.flexity.asia/` | Legacy flexity_admin Flask | вне scope этого документа |

```text
www.flexity.asia          flexity.asia
       │                        │
       ▼                        ├── /api/      → uvicorn :8005 (CoreOps)
  /var/www/                     ├── /console/  → static dist/ (SPA)
  flexity-landing               ├── /trailers/ → :8003
  (из landing/www/)             └── /          → Consult :8002 (legacy)
```

**Важно:** корень `flexity.asia/` остаётся Consult до отдельного этапа миграции. Console и API живут **рядом**, под префиксами `/console/` и `/api/`.

---

## Пути на сервере (рекомендуемые)

| Компонент | Путь в git | Путь на сервере |
|-----------|------------|-----------------|
| Backend code | `backend/` | `/opt/flexity/coreops/backend/` |
| Console build | `platform-console/dist/` | `/opt/flexity/coreops/platform-console/dist/` |
| Landing static | `landing/www/` | `/var/www/flexity-landing/` |

Кнопка «Войти в систему» на лендинге должна вести на:

```text
https://flexity.asia/console/login
```

Не на `admin.flexity.asia` и не на корень `flexity.asia/` (Consult).

---

## Build Platform Console

Выполнять **на сервере** или локально с последующей выкладкой `dist/` (по approval).

### Локально / на сервере

```bash
cd platform-console
cp .env.example .env.production
# Production API (same-origin, без CORS):
# VITE_API_BASE_URL=https://flexity.asia/api/v1

npm ci          # approval: npm на сервере
npm run build
ls -la dist/
```

Ожидаемый результат build (после Stage A):

- `dist/index.html` — script/link с префиксом `/console/assets/...`
- `dist/assets/*.js`, `*.css`

Проверка артефактов перед deploy:

```bash
grep -E 'src=|href=' dist/index.html
# ожидается: /console/assets/...
```

### Обновление после `git pull`

```bash
cd /opt/flexity/coreops
git pull
cd platform-console
npm ci && npm run build
# nginx reload — только с approval (см. ниже)
```

---

## Nginx: `flexity.asia` — Platform Console

Блоки добавлять в `flexity.asia.conf` **выше** `location /` (Consult), **рядом** с уже существующим `location ^~ /api/` (см. [flexity-asia-nginx.md](flexity-asia-nginx.md)).

### Редирект без слэша

```nginx
    location = /console {
        return 301 /console/;
    }
```

### Статика SPA + fallback

Рекомендуемый вариант (`alias` на `dist/`; Vite кладёт `index.html` в корень `dist/`):

```nginx
    # --- Platform Console (static SPA) ---
    location ^~ /console/assets/ {
        alias /opt/flexity/coreops/platform-console/dist/assets/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location ^~ /console/ {
        alias /opt/flexity/coreops/platform-console/dist/;
        index index.html;
        try_files $uri $uri/ /console/index.html;
    }
```

**Почему отдельный блок для `/console/assets/`:** hashed assets (`index-BwI87Uck.js`) можно кэшировать долго (`immutable`). `index.html` — без долгого кэша (см. ниже).

### Кэш для `index.html` (не кэшировать долго)

Если nginx отдаёт `index.html` через общий `location ^~ /console/`, добавьте исключение:

```nginx
    location = /console/index.html {
        alias /opt/flexity/coreops/platform-console/dist/index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        expires off;
    }
```

Либо после deploy проверяйте заголовки:

```bash
curl -sI https://flexity.asia/console/index.html | grep -i cache
```

### SPA fallback и deep links

Без fallback маршруты вроде `/console/login` и `/console/tenants` при **прямом заходе** или **refresh** вернут nginx 404.

| URL | Ожидание |
|-----|----------|
| `/console/` | `dist/index.html` |
| `/console/login` | `dist/index.html` (React Router) |
| `/console/tenants/uuid` | `dist/index.html` (React Router) |
| `/console/assets/*.js` | реальный файл из `dist/assets/` |

### Если `try_files` + `alias` не срабатывает (fallback 404)

На некоторых версиях nginx `try_files` с `alias` ведёт себя неочевидно. Запасной вариант — named location:

```nginx
    location ^~ /console/ {
        alias /opt/flexity/coreops/platform-console/dist/;
        try_files $uri $uri/ @console_fallback;
    }

    location @console_fallback {
        rewrite ^ /console/index.html break;
        alias /opt/flexity/coreops/platform-console/dist/index.html;
    }
```

Перед `nginx reload` обязательно: `sudo nginx -t`.

### Полный фрагмент (Console + API, без Consult)

Порядок `location` важен — более специфичные префиксы выше `location /`:

```nginx
    # --- CoreOps API (уже может быть в конфиге) ---
    location ^~ /api/ {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # --- Platform Console ---
    location = /console {
        return 301 /console/;
    }

    location ^~ /console/assets/ {
        alias /opt/flexity/coreops/platform-console/dist/assets/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location = /console/index.html {
        alias /opt/flexity/coreops/platform-console/dist/index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        expires off;
    }

    location ^~ /console/ {
        alias /opt/flexity/coreops/platform-console/dist/;
        index index.html;
        try_files $uri $uri/ /console/index.html;
    }

    # --- Legacy Consult (не менять без отдельного решения) ---
    location / {
        proxy_pass http://127.0.0.1:8002;
        # ... существующие proxy_set_header ...
    }
```

---

## Nginx: `www.flexity.asia` — Landing

Файлы в репозитории: `landing/www/` (Stage B ✅). На сервере — выкладка в `/var/www/flexity-landing/` при live deploy.

```nginx
server {
    listen 443 ssl http2;
    server_name www.flexity.asia;

    root /var/www/flexity-landing;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|webp)$ {
        expires 7d;
        add_header Cache-Control "public";
        access_log off;
    }
}
```

### Deploy landing (документировать, не выполнять без approval)

```bash
# с рабочей машины или CI — только с approval
rsync -av --delete landing/www/ user@server:/var/www/flexity-landing/

# на сервере
sudo nginx -t && sudo systemctl reload nginx
```

Проверка ссылки входа на лендинге:

```bash
grep -o 'href="[^"]*"' /var/www/flexity-landing/index.html | grep -i console
# ожидается: https://flexity.asia/console/login
```

---

## Deploy checklist (порядок действий)

Выполнять только с явным approval на ssh/scp/nginx.

1. [ ] `git pull` в `/opt/flexity/coreops`
2. [ ] `cd platform-console && npm ci && npm run build`
3. [ ] Проверить `dist/index.html` (пути `/console/assets/`)
4. [ ] Добавить/обновить nginx blocks для `/console/` (и www при наличии landing)
5. [ ] `sudo nginx -t`
6. [ ] `sudo systemctl reload nginx`
7. [ ] Smoke (см. ниже)
8. [ ] Убедиться, что Consult `/` и Trailers `/trailers/` не сломаны

**Не трогать:** `coreops.service`, PostgreSQL, alembic, backend `.env` — для console deploy не требуется.

---

## Smoke checklist после deploy

### Platform Console

| # | Проверка | Команда / действие | Ожидание |
|---|----------|-------------------|----------|
| 1 | Console root | `curl -sI https://flexity.asia/console/` | HTTP 200 |
| 2 | Login deep link | Открыть `https://flexity.asia/console/login` | Страница логина, не nginx 404 |
| 3 | SPA refresh | Залогиниться → `/console/tenants` → F5 | Список tenants, не 404 |
| 4 | Assets | DevTools Network: `*.js`, `*.css` | 200, путь `/console/assets/...` |
| 5 | API health | `curl -s https://flexity.asia/api/v1/health` | `{"status":"ok"}` или аналог |
| 6 | API from UI | Login в консоли | Запросы на `/api/v1/*`, не на `:8005` напрямую |
| 7 | Wrong role | Login не-provider (если есть) | Access denied в SPA |

### API same-origin

Консоль в production должна использовать:

```env
VITE_API_BASE_URL=https://flexity.asia/api/v1
```

В браузере (Network tab после login):

- `POST https://flexity.asia/api/v1/auth/login` → 200
- `GET https://flexity.asia/api/v1/tenants` → 200 (с Bearer)

Не должно быть запросов на `http://127.0.0.1:8005` из браузера.

### Landing (после Stage B)

| # | Проверка | Ожидание |
|---|----------|----------|
| 1 | `curl -sI https://www.flexity.asia/` | HTTP 200 |
| 2 | CSS/JS/images | 200 |
| 3 | Кнопка «Войти в систему» | → `https://flexity.asia/console/login` |

### Legacy coexistence (не сломать)

| # | Проверка | Ожидание |
|---|----------|----------|
| 1 | `curl -sI https://flexity.asia/` | Consult как раньше |
| 2 | `curl -sI https://flexity.asia/trailers/` | Trailers как раньше |
| 3 | `curl -s https://flexity.asia/api/v1/health` | CoreOps ok |

---

## Rollback

### Быстрый rollback Console (без backend)

1. Удалить или закомментировать блоки `location` для `/console/` в `flexity.asia.conf`.
2. `sudo nginx -t && sudo systemctl reload nginx` (с approval).
3. Опционально удалить `platform-console/dist/` на сервере.

Consult на `/` продолжит работать — блок `location /` не менялся.

### Rollback nginx config целиком

```bash
# восстановить backup конфига (путь зависит от сервера)
sudo cp /etc/nginx/sites-available/flexity.asia.conf.bak /etc/nginx/sites-available/flexity.asia.conf
sudo nginx -t && sudo systemctl reload nginx
```

Рекомендация: перед первым reload сохранить копию:

```bash
sudo cp /etc/nginx/sites-available/flexity.asia.conf /etc/nginx/sites-available/flexity.asia.conf.bak.$(date +%Y%m%d)
```

### Rollback landing

```bash
# восстановить предыдущий snapshot /var/www/flexity-landing/
rsync -av /var/www/flexity-landing.backup/ /var/www/flexity-landing/
sudo nginx -t && sudo systemctl reload nginx
```

### Что не откатывать при rollback console/landing

| Компонент | Действие |
|-----------|----------|
| PostgreSQL / CoreOps DB | **не трогать** |
| `coreops.service` | **не останавливать** (API остаётся) |
| Alembic migrations | **не откатывать** |
| Consult / Trailers | только если их блоки не менялись |

---

## Troubleshooting

| Симптом | Вероятная причина | Действие |
|---------|-------------------|----------|
| Белая страница `/console/` | Неверный `base` в build | Пересобрать с `base: "/console/"` (Stage A) |
| 404 на `/console/assets/*.js` | nginx alias path | Проверить путь к `dist/assets/` |
| 404 на refresh `/console/tenants` | нет SPA fallback | Добавить `try_files` / `@console_fallback` |
| API CORS error | неверный `VITE_API_BASE_URL` | Использовать `https://flexity.asia/api/v1` |
| Login ok, API 401 | clock skew / expired token | Проверить время сервера, refresh flow |
| `localhost` proxy fail (dev) | Windows `::1` | Dev: `127.0.0.1` в vite proxy (Stage A) |

---

## Статус этапов репозитория

| Этап | Содержание | Статус |
|------|------------|--------|
| A | `base` + `basename` `/console/`, vite proxy `127.0.0.1` | ✅ выполнен |
| B | `landing/www/` в репозитории | ✅ выполнен |
| C | этот документ | ✅ |

`landing/www/` в git: `index.html`, `assets/` (logo, favicon), ссылка входа → `https://flexity.asia/console/login`. Live deploy landing на `www.flexity.asia` — отдельный этап с approval (rsync + nginx).
