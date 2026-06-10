# Implementation Plan: Console & Landing Deploy Prep

**Дата:** 2026-06-10  
**Research brief:** [2026-06-09-flexity-platform-console-research-brief.md](../research/2026-06-09-flexity-platform-console-research-brief.md)  
**Предыдущий plan:** [2026-06-09-platform-console-mvp-implementation-plan.md](2026-06-09-platform-console-mvp-implementation-plan.md)  
**Статус:** waiting for approval — код не писать до явного approve

---

## Goal

Подготовить Flexity к production-размещению **Platform Console** и **публичного лендинга** без изменений backend и без выполнения deploy на сервер.

Целевые URL после deploy (отдельный этап, не в этом плане):

| URL | Назначение |
|-----|------------|
| `https://www.flexity.asia/` | Публичный лендинг (статика из `landing/www/`) |
| `https://flexity.asia/console/login` | Platform Console (SPA из `platform-console/dist/`) |
| `https://flexity.asia/api/v1/*` | Flexity FastAPI (уже описано в `deploy/flexity-asia-nginx.md`) |

**Не трогаем:** legacy Consult на `flexity.asia/`, `admin.flexity.asia`, Trailers, flexity_admin Flask.

---

## Classification

| Поле | Значение |
|------|----------|
| **Project** | Flexity |
| **Category** | `platform_core` (frontend path prep) + `documentation_only` (deploy docs, этап C) |
| **Risk** | low–medium |
| **Backend changes** | **none** |
| **Migrations** | **none** |
| **Live deploy** | **none** (только документация и локальная подготовка) |

### Task Classification (coordinator)

1. **Project:** Flexity  
2. **Category:** `platform_core` + `documentation_only`  
3. **Risk level:** low–medium  
4. **Intended scope:** `platform-console/`, `landing/`, `docs/deploy/` или `deploy/` (только docs)  
5. **Forbidden scope:** `backend/`, `flexity_admin/`, Trailers, Consulting Flask, nginx/systemd на сервере, `.env` production  
6. **Required plan:** implementation plan (этот файл) → approval → код/docs по этапам A→B→C  

---

## Current state (baseline)

| Компонент | Состояние |
|-----------|-----------|
| `platform-console/` | Vite + React + TS MVP создан (2026-06-09 plan) |
| `vite.config.ts` | `proxy` → `http://localhost:8000` (ломается на Windows из-за `localhost` → `::1`) |
| `BrowserRouter` | без `basename` (корень `/`) |
| `base` в Vite | не задан (по умолчанию `/`) |
| Лендинг www | на сервере, **исходников в git нет** |
| `flexity.asia/` | legacy Consult (порт 8002) |
| `deploy/flexity-asia-nginx.md` | описан только `/api/` → :8005, **нет `/console/`** |

---

## Architecture (target)

```text
flexity.asia
├── /api/          → FastAPI :8005          (уже есть)
├── /console/      → static SPA dist/       (новый nginx location)
└── /              → Consult :8002           (не трогаем в этом плане)

www.flexity.asia
└── /              → static landing/www/     (из репозитория)
```

Кнопка «Войти в систему» на лендинге → `https://flexity.asia/console/login` (не `admin.flexity.asia`, не Consult).

---

## Scope overview — 3 этапа

| Этап | Название | Тип | После approval |
|------|----------|-----|----------------|
| **A** | Console deploy prep | код в `platform-console/` | да |
| **B** | Landing in repo | статика + README | да |
| **C** | Deploy docs only | markdown, без ssh/nginx | да |

Этапы выполнять **последовательно**: A → B → C. Каждый этап — отдельный маленький commit (по запросу пользователя).

---

## Этап A — Console deploy prep

### Цель

Сделать SPA готовой к размещению под префиксом `/console/` и починить локальный dev proxy на Windows.

### Files to modify (exact)

| File | Change |
|------|--------|
| `platform-console/vite.config.ts` | `base: "/console/"`; proxy `target: "http://127.0.0.1:8000"` |
| `platform-console/src/main.tsx` | `<BrowserRouter basename="/console">` |
| `platform-console/README.md` | обновить dev URL, smoke checklist под `/console/` |

### Files to verify (read-only, без изменений если работают)

| File | Проверить |
|------|-----------|
| `platform-console/src/routes.tsx` | пути `/login`, `/tenants` — относительные, с `basename` резолвятся в `/console/login` |
| `platform-console/src/auth/ProtectedRoute.tsx` | `Navigate to="/login"` — OK с basename |
| `platform-console/src/pages/*.tsx` | `Link`, `useNavigate` — относительные пути |
| `platform-console/.env.example` | `VITE_API_BASE_URL=/api/v1` — same-origin в prod, proxy в dev |
| `platform-console/index.html` | Vite сам подставит `/console/` для assets при build |

### Детали реализации A

#### 1. `vite.config.ts`

```ts
export default defineConfig({
  base: "/console/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",  // не localhost — обход ::1 на Windows
        changeOrigin: true,
      },
    },
  },
});
```

**Почему `127.0.0.1`:** на Windows Node/Vite резолвит `localhost` в IPv6 `::1`, а uvicorn часто слушает только `127.0.0.1` → proxy ECONNREFUSED.

#### 2. React Router `basename`

В `main.tsx`:

```tsx
<BrowserRouter basename="/console">
```

Все существующие маршруты (`/login`, `/tenants`, …) остаются без префикса в коде — React Router добавит `/console` автоматически.

#### 3. Dev URL (важно)

После `base` и `basename` dev-точка входа:

```text
http://localhost:5173/console/
http://localhost:5173/console/login
```

Корень `http://localhost:5173/` **не** откроет приложение — это ожидаемое поведение Vite с `base: "/console/"`.

#### 4. Production build

```bash
cd platform-console
npm run build
# dist/index.html, dist/assets/* — пути с префиксом /console/
```

Для локальной проверки build:

```bash
npm run preview
# открыть http://localhost:4173/console/
```

`VITE_API_BASE_URL` для production build (при будущем deploy):

```env
VITE_API_BASE_URL=https://flexity.asia/api/v1
```

В этапе A **не менять** `.env` в репозитории — только задокументировать в README.

### Этап A — out of scope

- CORS middleware в backend
- изменение `deploy/flexity-asia-nginx.md` (это этап C)
- production `.env` на сервере
- `npm install` новых пакетов (не требуется)

---

## Этап B — Landing in repo

### Цель

Версионировать публичный лендинг в репозитории и направить кнопку входа на новую Platform Console.

### Files to create (exact)

| Path | Purpose |
|------|---------|
| `landing/README.md` | источник файлов, локальный preview, ссылка на console |
| `landing/www/index.html` | главная страница лендинга |
| `landing/www/assets/**` | CSS, JS, images, fonts (как на www.flexity.asia) |

Структура:

```text
landing/
  README.md
  www/
    index.html
    assets/
      css/...
      js/...
      img/...
      (прочие файлы с сервера)
```

### Источник контента (без ssh в этом плане)

Исходников в git нет. При реализации этапа B — **один** из способов (выбрать при approve):

| Способ | Команда / действие | Approval |
|--------|-------------------|----------|
| **B1 — wget/curl с prod** | `wget -r -np -k -P landing/tmp https://www.flexity.asia/` затем нормализация в `landing/www/` | network fetch — ok локально |
| **B2 — ручная копия** | пользователь копирует файлы с сервера в `landing/www/` | без network |
| **B3 — архив от пользователя** | распаковать предоставленный zip | без network |

**Предпочтение:** B1 (wget) — воспроизводимо, если www доступен публично.

### Обязательное изменение в `landing/www/index.html`

Найти кнопку/ссылку «Войти в систему» (или аналог) и установить:

```html
<a href="https://flexity.asia/console/login">Войти в систему</a>
```

### Запрещённые ссылки на лендинге

Убрать или заменить ссылки, ведущие в legacy Flask:

| Было (примеры) | Нельзя оставлять |
|----------------|------------------|
| `admin.flexity.asia/auth/login` | legacy flexity_admin |
| `flexity.asia/` как «войти» | legacy Consult OS |
| любые `/auth/login` на Consult | legacy |

Допустимые внешние ссылки: WhatsApp, Telegram, демо-заявки, якоря на той же странице.

### `landing/README.md` — содержание

1. Назначение папки (source of truth для www.flexity.asia).  
2. Как обновить с сервера (кратко).  
3. Локальный preview: `cd landing/www && python -m http.server 8080` → `http://localhost:8080/`.  
4. Целевой deploy path на сервере (документировать, не выполнять): например `/var/www/flexity-landing/` или существующий docroot www.  
5. Ссылка входа: `https://flexity.asia/console/login`.

### Этап B — out of scope

- изменение nginx для www (этап C)  
- SEO-редизайн лендинга  
- CMS / сборщик  
- backend forms для заявок (если есть — оставить как на оригинале или заглушка `#` с пометкой в README)

---

## Этап C — Deploy docs only

### Цель

Задокументировать nginx и deploy-процедуру. **Не выполнять** ssh, scp, nginx reload, systemd.

### Files to create or extend (exact)

| File | Action |
|------|--------|
| `deploy/console-and-landing.md` | **создать** — полная инструкция |
| `deploy/flexity-asia-nginx.md` | **добавить ссылку** на новый doc (1–2 строки, без переписывания) |

### Содержание `deploy/console-and-landing.md`

#### 1. Platform Console — nginx `location /console/`

Блоки добавлять **выше** `location /` (Consult), **ниже или рядом** с `location ^~ /api/`:

```nginx
    # --- Platform Console (static SPA) ---
    location ^~ /console/ {
        alias /opt/flexity/coreops/platform-console/dist/;
        try_files $uri $uri/ /console/index.html;
    }
```

**Альтернатива** (если `alias` + `try_files` неудобен на конкретном nginx):

```nginx
    location /console {
        return 301 /console/;
    }

    location ^~ /console/ {
        root /opt/flexity/coreops/platform-console/dist;
        # при root путь на диске: dist/console/index.html — см. примечание ниже
        try_files $uri $uri/ /console/index.html;
    }
```

**Примечание для исполнителя deploy:** при `base: "/console/"` Vite кладёт `index.html` в `dist/index.html`, а assets в `dist/assets/`. С `alias` на `dist/` URL `/console/` → `dist/index.html`. Проверить на staging перед reload.

SPA fallback обязателен: без `try_files ... /console/index.html` deep links (`/console/tenants/...`) дадут 404.

#### 2. Build console на сервере (документировать, не выполнять)

```bash
cd /opt/flexity/coreops/platform-console
cp .env.example .env.production   # VITE_API_BASE_URL=https://flexity.asia/api/v1
# npm ci && npm run build  — только с approval npm на сервере
ls -la dist/
```

#### 3. Landing www — nginx

Отдельный server block или существующий `www.flexity.asia`:

```nginx
    server_name www.flexity.asia;

    root /var/www/flexity-landing;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
```

Deploy landing (документировать):

```bash
# rsync/scp — только с approval
rsync -av landing/www/ user@server:/var/www/flexity-landing/
sudo nginx -t && sudo systemctl reload nginx   # approval required
```

#### 4. Проверки после deploy (smoke, для будущего)

```bash
curl -sI https://flexity.asia/console/
curl -sI https://flexity.asia/console/login
curl -s https://flexity.asia/api/v1/health
curl -sI https://www.flexity.asia/
# Consult не сломан:
curl -sI https://flexity.asia/
```

#### 5. Coexistence matrix (зафиксировать в doc)

| URL | Сервис | Трогаем в этом deploy? |
|-----|--------|------------------------|
| `flexity.asia/` | Consult :8002 | **Нет** |
| `flexity.asia/trailers/` | Trailers :8003 | **Нет** |
| `flexity.asia/api/` | CoreOps :8005 | **Нет** (уже есть) |
| `flexity.asia/console/` | Platform Console static | **Да** (новый) |
| `www.flexity.asia/` | Landing static | **Да** (из repo) |
| `admin.flexity.asia` | legacy Flask | **Нет** |

### Этап C — out of scope

- выполнение любых команд на сервере  
- изменение `coreops.service`  
- SSL cert changes  
- DNS changes  

---

## Files not to touch (forbidden)

| Path | Reason |
|------|--------|
| `backend/**` | backend не менять |
| `backend/alembic/**` | no migrations |
| `flexity_admin/**` | legacy reference |
| Trailers repo | live legacy |
| Consulting Flask | live legacy |
| `backend/.env`, production secrets | no env changes |
| `deploy/coreops.service` | systemd — отдельный approval |
| nginx config на сервере | deploy — отдельный approval |
| `.cursor/rules/**` | orchestration meta |

---

## Implementation steps (after approval)

### Step 0 — Approval gate

Получить явный approve: `approve console-and-landing deploy prep plan`.

Опционально по этапам:

- `approve stage A` — только platform-console  
- `approve stage B` — landing + wget если нужен  
- `approve stage C` — deploy docs only  

### Step 1 — Этап A (код)

1. Правка `vite.config.ts` (`base`, `127.0.0.1`).  
2. Правка `main.tsx` (`basename`).  
3. Обновить `platform-console/README.md`.  
4. Локальные проверки (см. Tests/checks).  

### Step 2 — Этап B (статика)

1. Получить файлы лендинга (B1/B2/B3).  
2. Разложить в `landing/www/`.  
3. Исправить href «Войти в систему».  
4. Написать `landing/README.md`.  
5. Локальный preview + проверка ссылок.  

### Step 3 — Этап C (docs)

1. Создать `deploy/console-and-landing.md`.  
2. Добавить cross-link в `deploy/flexity-asia-nginx.md`.  
3. Self-review: нет инструкций, требующих немедленного ssh.  

---

## Tests / checks

### Этап A — локально

**Prerequisites:** backend на `http://127.0.0.1:8000`, provider_owner существует.

| # | Command / action | Expected |
|---|------------------|----------|
| A1 | `cd backend && curl -s http://127.0.0.1:8000/api/v1/health` | `{"status":"ok"}` или аналог |
| A2 | `cd platform-console && npm run dev` | Vite стартует без ошибок |
| A3 | Open `http://localhost:5173/console/` | Redirect → `/console/login` |
| A4 | Login provider_owner | → `/console/tenants` |
| A5 | Network tab: API calls | `/api/v1/*` → 200 (proxy на 127.0.0.1:8000) |
| A6 | `npm run build` | exit 0, `dist/` создан |
| A7 | `npm run preview` + open `/console/login` | SPA грузится, assets 200 |
| A8 | Inspect `dist/index.html` | script/link paths начинаются с `/console/` |
| A9 | `cd backend && python -m pytest` | без регрессии (backend не менялся) |

### Этап B — локально

| # | Command / action | Expected |
|---|------------------|----------|
| B1 | `cd landing/www && python -m http.server 8080` | сервер стартует |
| B2 | Open `http://localhost:8080/` | лендинг как на www |
| B3 | Click «Войти в систему» | href = `https://flexity.asia/console/login` |
| B4 | Grep legacy URLs | нет `admin.flexity.asia`, нет Consult login |
| B5 | Assets load | CSS/JS/images 200 |

```bash
# B4 — проверка ссылок
grep -rE 'admin\.flexity|/auth/login' landing/www/ || echo "OK: no legacy login links"
```

### Этап C — review only

| # | Check | Expected |
|---|-------|----------|
| C1 | `deploy/console-and-landing.md` exists | да |
| C2 | nginx blocks для `/console/` и www | описаны |
| C3 | doc не содержит «выполнить сейчас ssh» без approval gate | да |
| C4 | coexistence table | Consult/Trailers не ломаем |

### Commands reference (copy-paste)

```bash
# Terminal 1 — Backend
cd backend
docker compose up --build
# или: uvicorn с 127.0.0.1:8000

# Terminal 2 — Console dev
cd platform-console
npm run dev
# → http://localhost:5173/console/

# Build
cd platform-console
npm run build
npm run preview
# → http://localhost:4173/console/

# Landing local
cd landing/www
python -m http.server 8080
# → http://localhost:8080/

# Backend regression
cd backend
python -m pytest
```

---

## Smoke checklist (post-implementation, local)

Полный чеклист перед будущим production deploy:

### Platform Console

- [ ] `http://localhost:5173/console/` → login  
- [ ] Login → tenants list  
- [ ] Create tenant (starter + kindergarten_basic)  
- [ ] Tenant detail: modules, subscription, labels  
- [ ] Logout → login blocked without token  
- [ ] `npm run build` + preview: `/console/login` works  
- [ ] API через same-origin path `/api/v1` (dev proxy)  

### Landing

- [ ] Главная открывается локально  
- [ ] Все assets грузятся  
- [ ] «Войти в систему» → `https://flexity.asia/console/login`  
- [ ] Нет ссылок на legacy Flask login  

### Docs

- [ ] `deploy/console-and-landing.md` читается end-to-end  
- [ ] Понятно, куда класть `dist/` и `landing/www/` на сервере  

### Future production smoke (после отдельного deploy approval)

- [ ] `https://flexity.asia/console/login` — 200, SPA  
- [ ] `https://flexity.asia/api/v1/health` — ok  
- [ ] `https://www.flexity.asia/` — лендинг  
- [ ] `https://flexity.asia/` — Consult как раньше  
- [ ] Кнопка на www → console login  

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Windows `localhost` → `::1` | dev proxy broken | `127.0.0.1` в vite proxy |
| `base` + `basename` mismatch | 404 assets, blank page | оба = `/console`, проверить A7–A8 |
| nginx `alias` + SPA fallback | deep links 404 | `try_files` в deploy doc, staging test |
| Лендинг без исходников | неполная копия | wget + diff с live www |
| Случайные legacy login links | пользователи в Consult | grep + ручная проверка B4 |
| CORS в prod | API fails from console origin | same-origin `/api/` — уже так в target arch |
| Consult root vs console | путаница URL | документировать в README и landing |
| Большие binary assets в git | repo bloat | только необходимые файлы; при необходимости CR на CDN позже |

---

## Rollback

### Этап A

```bash
git checkout -- platform-console/vite.config.ts platform-console/src/main.tsx platform-console/README.md
```

### Этап B

```bash
git rm -r landing/
# или git checkout -- landing/ если уже committed
```

### Этап C

```bash
git rm deploy/console-and-landing.md
git checkout -- deploy/flexity-asia-nginx.md
```

### Full rollback

```bash
git revert <commit-range>
```

**Не требуется rollback:** backend DB, migrations, server nginx (не трогали).

---

## What requires approval

| Item | When | Default in this plan |
|------|------|----------------------|
| Этот implementation plan | перед любым кодом | ⏳ waiting |
| Этап A code changes | после plan approve | ⏳ waiting |
| Этап B landing import (wget) | при способе B1 | ⏳ waiting |
| Этап C deploy docs | после A+B или параллельно docs-only | ⏳ waiting |
| `npm install` | только если lockfile устарел | обычно не нужен |
| `npm run build` / `npm run dev` | локальная проверка | ✅ safe после approve A |
| ssh / scp / rsync | production deploy | ❌ не в этом плане |
| `nginx -t` / `systemctl reload nginx` | production | ❌ не в этом плане |
| Backend / migrations / CORS | отдельный plan | ❌ forbidden |

**Чтобы начать:** напиши `approve console-and-landing deploy prep plan` или `approve stage A`.

---

## Dependencies

Новые npm-пакеты **не требуются**. Используется существующий `platform-console/package.json`.

---

## Future work (not this plan)

| Track | Content |
|-------|---------|
| Deploy execution | ssh, build on server, nginx reload — отдельный live deploy plan |
| Backend CORS | если console на отдельном subdomain |
| `flexity.asia/` root migration | Consult → landing или redirect — product decision |
| Track A backend | user invite, memberships — отдельный plan |
| Open question из research | `console.flexity.asia` vs `/console` — **решено:** `/console` |

---

## Approval

| Item | Status |
|------|--------|
| Research brief 2026-06-09 | ✅ |
| Platform Console MVP plan 2026-06-09 | ✅ (код создан) |
| **This plan (deploy prep A+B+C)** | ⏳ **waiting for approval** |
| Code / landing files | ⏳ waiting |
| Server deploy | ❌ not in scope |

---

## Final checks (plan author)

- [x] Classification documented  
- [x] Exact files for stages A, B, C  
- [x] Forbidden files listed  
- [x] Verification commands listed  
- [x] Approval gates explicit  
- [x] Rollback per stage  
- [x] Smoke checklist local + future prod  
- [x] Backend / migrations / deploy execution — not touched  
- [x] No code written in this task  
