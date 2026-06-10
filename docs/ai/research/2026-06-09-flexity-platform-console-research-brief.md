# Research Brief: Flexity Platform Console (Superadmin UI)

**Дата:** 2026-06-09  
**Тип задачи:** platform_core / frontend / research_only  
**Статус:** read-only анализ, код не изменялся

---

## Context

Flexity — целевая FastAPI multi-tenant SaaS ERP. Flask-проекты (Trailers, flexity_admin) — legacy/reference, не целевая платформа.

Нужен **Platform Console** — внутренний UI для владельца платформы (superadmin / provider owner): управление tenants, подписками, модулями, industry templates, аудитом.

В репозитории `flexity_admin` исторически задуман как «кабинет владельца», но фактически реализован как **Consulting OS** одного клиента. Во Flexity backend уже есть ~30 REST endpoints для platform operations, но **frontend отсутствует** (Swagger only).

Цель этого brief — зафиксировать текущее состояние, gaps и рекомендацию по первому frontend без написания кода.

---

## Current state

### 1. Что такое flexity_admin (Flask)

| Аспект | Факт |
|--------|------|
| **Репозиторий** | `flexity_admin` |
| **Задумка (AGENTS.md)** | Кабинет владельца платформы: tenants, подписки, организации клиентов, доступы |
| **Фактический код** | **Consulting OS** — single-tenant ERP/CRM для одной консалтинговой компании (бренд Ziza.projects) |
| **Стек** | Flask, SQLAlchemy, Alembic, Flask-Login, Jinja2 + Bootstrap 5, SQLite/PostgreSQL |
| **Entry point** | `wsgi.py` → `create_app()` в `app/__init__.py` |
| **Blueprints** | 9: `auth`, `core`, `crm`, `reports`, `manager`, `director`, `assistant`, `tasks`, `documents` |
| **Multi-tenant** | **Нет** — нет моделей tenant, subscription, platform billing |
| **Хостинг** | `admin.flexity.asia` — домен есть, функционально это не Platform Console |

**Вывод:** flexity_admin **не является** готовой Platform Console. Это reference для будущего `consulting_basic` industry template во Flexity, а не runtime для superadmin.

#### Роли и auth (flexity_admin)

| Роль | Назначение |
|------|------------|
| `director` | Полный доступ: финансы, договоры, отчёты, справочники, комиссии |
| `sales_manager` | Свои лиды/клиенты/проекты, CRM, без платежей/договоров |
| `assistant` | Inbox, платежи, дебиторка/кредиторка |
| `project_manager` | Проекты, поставщики, документы, задачи |
| `client`, `supplier` | Объявлены, в routes не используются |

Механизм: `User` + M2M `Role`, `@login_required`, `@roles_required`, фильтры в `app/services/user_access.py`.

---

### 2. Экраны/процессы flexity_admin, полезные для Platform Console

#### Прямо применимы к Platform Console

| Паттерн flexity_admin | Будущий экран Platform Console | Примечание |
|-----------------------|-------------------------------|------------|
| Login / logout | `/login` | JWT вместо Flask-Login session |
| Director dashboard (KPI) | Platform dashboard | tenants count, trial/active/suspended, security events |
| Role-based sidebar | Console navigation | provider_owner vs будущие provider roles |
| `/dict/*` справочники | Plans, modules registry, templates catalog | read-only на MVP, CRUD позже |
| `/assistant/inbox` (алерты) | Platform alerts | просроченные trial, suspended tenants, failed logins |
| Activity / audit mindset | Audit logs viewer | уже есть API `/audit/*` |

#### Полезны как UX-reference, но не для Platform Console

| Экран flexity_admin | Куда в Flexity | Почему не Platform Console |
|---------------------|----------------|---------------------------|
| CRM leads, webhook Instagram | `workflows` + `integrations` (tenant-level) | Операции внутри tenant, не платформы |
| Clients, orders, contracts, acts | `parties`, `documents`, `finance` | Tenant ERP |
| Payments, P&L, receivables | `finance` module | Tenant finance |
| Manager commissions | consulting_basic template | Отраслевая логика |
| Consultations + Google Calendar | integrations | Tenant feature |
| Tasks, documents requests | `workflows` | Tenant ops |

#### Vision из AGENTS.md, которого нет ни в flexity_admin, ни полностью во Flexity API

- Управление подписками и оплатами платформы (billing)
- Управление пользователями платформы (invite, disable)
- Проекты внедрения по клиентам
- Impersonation / «зайти как tenant»
- Client/supplier portals

---

### 3. Что уже есть во Flexity FastAPI backend

**Базовый префикс:** `/api/v1`  
**Терминология:** отдельной сущности `superadmin` нет. Platform Console = пользователь с ролью **`provider_owner`** (`ProviderStaff`).

| Концепция UI | В коде |
|--------------|--------|
| Superadmin | `ProviderRole.PROVIDER_OWNER` |
| Bootstrap платформы | `POST /auth/register` (один раз, пока нет users) |
| Клиентский tenant | `Tenant` + `UserTenantMembership` |

#### 3.1 Auth

| Method | Path | Auth | Статус |
|--------|------|------|--------|
| POST | `/auth/register` | Публичный (bootstrap only) | ✅ |
| POST | `/auth/login` | Публичный | ✅ |
| POST | `/auth/refresh` | Публичный (refresh token) | ✅ |
| GET | `/auth/me` | Bearer access token | ✅ |

- JWT HS256, access 30 мин / refresh 7 дней
- Роли **не в JWT** — подгружаются в `/auth/me` (`provider_staff`, `tenant_memberships`)
- Security events пишутся при register/login/refresh

**Пробелы:** logout, смена пароля, invite/list/disable users, CRUD provider staff, роли кроме `provider_owner` объявлены, но не используются в guards.

#### 3.2 Tenants

| Method | Path | Auth | Статус |
|--------|------|------|--------|
| GET | `/tenants` | Authenticated (scope по роли) | ✅ |
| POST | `/tenants` | `provider_owner` | ✅ |
| GET | `/tenants/{tenant_id}` | Authenticated + access | ✅ |
| PATCH | `/tenants/{tenant_id}` | provider staff **или** `tenant_owner` | ✅ |
| POST | `/tenants/{tenant_id}/memberships` | `provider_owner` | ✅ |

**Provisioning при POST `/tenants`:**
1. Создание tenant
2. Опционально membership owner (`owner_user_id` / `owner_email`)
3. Все модули disabled
4. Опционально `plan_code` → subscription + trial modules
5. Опционально `industry_template_code` → apply template

**Пробелы:** DELETE tenant (только status via PATCH), GET memberships list, remove/update membership, пагинация/фильтры, aggregated tenant detail endpoint.

#### 3.3 Plans / Subscriptions

| Method | Path | Auth | Статус |
|--------|------|------|--------|
| GET | `/plans` | Authenticated | ✅ read-only catalog |
| GET | `/tenants/{tenant_id}/subscription` | `provider_owner` | ✅ |
| POST | `/tenants/{tenant_id}/subscription` | `provider_owner` | ✅ assign/upsert |

Seed: `starter`, `business`, `enterprise` + features + usage limits (`SEED_ON_STARTUP=true`).

**Пробелы:** CRUD планов/features/limits, subscription lifecycle (cancel/suspend), billing periods API, usage dashboard (`UsageEvent` пишется, read API нет).

#### 3.4 Modules

| Method | Path | Auth | Статус |
|--------|------|------|--------|
| GET | `/modules/registry` | Authenticated | ✅ глобальный каталог |
| GET | `/tenants/{tenant_id}/modules` | `provider_owner` | ✅ |
| GET | `/tenants/{tenant_id}/modules/{module_code}` | `provider_owner` | ✅ |
| PATCH | `/tenants/{tenant_id}/modules/{module_code}` | `provider_owner` | ✅ |
| POST | `/tenants/{tenant_id}/modules/{module_code}/enable` | `provider_owner` | ✅ |
| POST | `/tenants/{tenant_id}/modules/{module_code}/disable` | `provider_owner` | ✅ |
| PATCH | `/tenants/{tenant_id}/modules/{module_code}/mode` | `provider_owner` | ✅ |

Seed: 8 модулей (`parties`, `crm`, `catalog`, `documents`, `finance`, `accounting`, `integrations`, `ai`).

**Пробелы:** CRUD module definitions (только seed), bulk enable/disable, tenant self-service modules.

**Важно для UI:** два слоя «фич» — tenant modules (`enabled/trial/disabled`) и plan features (`crm.work_items.create`). Консоль должна показывать оба.

#### 3.5 Industry Templates

| Method | Path | Auth | Статус |
|--------|------|------|--------|
| GET | `/industry-templates` | Authenticated | ✅ |
| POST | `/industry-templates` | `provider_owner` | ✅ |
| GET | `/industry-templates/{template_id}` | Authenticated | ✅ |
| PATCH | `/industry-templates/{template_id}` | `provider_owner` | ✅ |
| POST | `/tenants/{tenant_id}/apply-template/{template_id}` | `provider_owner` | ✅ |

Apply включает: modules, labels, pipelines, custom fields, document templates, catalog items, AI agents.  
Seed: `kindergarten_basic`.

**Пробелы:** DELETE template, preview/dry-run apply, version history.

#### 3.6 Tenant Labels

| Method | Path | Auth | Статус |
|--------|------|------|--------|
| GET | `/tenants/{tenant_id}/labels` | provider staff **или** tenant member | ✅ read-only |

Labels живут в `TenantSettings.labels_config`. Запись — только через `apply-template`.

**Пробелы:** `PATCH /tenants/{id}/labels`, typed response schema (сейчас сырой `dict`).

#### 3.7 Audit

| Method | Path | Auth | Статус |
|--------|------|------|--------|
| GET | `/audit/logs` | Authenticated | ✅ |
| GET | `/audit/data-access` | Tenant context (`X-Tenant-ID`) | ✅ |
| GET | `/audit/security-events` | Authenticated | ✅ |

Query filters: `tenant_id`, `user_id`, `entity_type`, `action`/`event_type`, `limit` (1–500).  
Автозапись: middleware на mutating requests, security events в auth.

**Пробелы:** pagination (cursor/offset), export, platform-wide data-access без tenant header, dashboard aggregates.

#### Frontend во Flexity

**Отсутствует.** Репозиторий содержит только `backend/`, deploy, docs. README явно: «Полноценный frontend — не входит в MVP».

---

### 4. Endpoint gaps для первого Superadmin UI

#### MVP-экраны, которые можно собрать **на существующем API**

| # | Экран | Endpoints | Backend gaps |
|---|-------|-----------|--------------|
| 1 | Login | `POST /auth/login`, `GET /auth/me`, `POST /auth/refresh` | logout (можно обойти client-side) |
| 2 | Tenants list | `GET /tenants` | пагинация, фильтры по status |
| 3 | Tenant detail | `GET /tenants/{id}` + 3–4 параллельных запроса | нет aggregated detail |
| 4 | Create tenant wizard | `POST /tenants` + `GET /plans` + `GET /industry-templates` | нет preview provisioning |
| 5 | Tenant modules | `GET/PATCH/enable/disable /tenants/{id}/modules/*` | bulk ops |
| 6 | Subscription | `GET /plans`, `GET/POST /tenants/{id}/subscription` | cancel/suspend |
| 7 | Templates | `GET/POST/PATCH /industry-templates`, apply | delete, dry-run |
| 8 | Labels preview | `GET /tenants/{id}/labels` | edit |
| 9 | Audit | `GET /audit/security-events`, `GET /audit/logs?tenant_id=` | pagination |

#### Критичные gaps (консоль «неполноценна» без них)

| Gap | Влияние на UI | Приоритет |
|-----|---------------|-----------|
| User management (invite, list, disable, reset password) | Нельзя добавить tenant owner без ручного register | **P0** |
| `GET /tenants/{id}/memberships` | Нельзя показать пользователей tenant | **P0** |
| `PATCH /tenants/{id}/labels` | Labels только read-only | P1 |
| Plan admin CRUD | Тарифы только из seed | P1 |
| Subscription lifecycle | Только assign, нет cancel/suspend UI | P1 |
| Usage monitoring read API | Нет экрана лимитов | P2 |
| Platform dashboard aggregate | 5+ запросов для KPI | P2 |
| Pagination на списках | Проблема при росте tenants | P2 |
| Impersonation | Нельзя «зайти в tenant» из консоли | P3 |

#### Архитектурные нюансы для UI

1. **Provider owner everywhere** — даже `provider_admin` в enum не получит доступ к modules/subscriptions routes.
2. **Bootstrap lock** — после первого register новых provider companies через API создать нельзя.
3. **Tenant context** — операции внутри tenant (parties, CRM…) требуют header `X-Tenant-ID`; консоль должна его прокидывать при drill-down.
4. **CORS** — при отдельном frontend origin нужна настройка FastAPI CORS (сейчас не проверялось в brief, учесть при deploy).

---

### 5. Рекомендация по frontend

#### Варианты

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **Vite + React SPA** | Быстрый старт, простой стек, идеален для internal admin | Нет SSR (не нужен для консоли) |
| **Next.js App Router** | SSR, file-based routing, middleware auth | Избыточен для internal tool; сложнее deploy рядом с FastAPI |
| **Продолжать Flask Jinja (flexity_admin)** | Привычный стек | **Противоречит архитектуре** — не целевая платформа |
| **Swagger/Redoc only** | Уже есть | Не UX для ежедневной работы |

#### Рекомендация: **отдельный Vite + React admin** (не Next.js) на Phase 1

**Почему Vite, а не Next.js:**

1. Platform Console — **внутренний** инструмент для 1–5 provider staff. SEO, SSR, edge rendering не нужны.
2. API уже REST + JWT — классический SPA с `Authorization: Bearer` достаточен.
3. Меньше moving parts: нет Node server в production (статика через nginx рядом с `/api/`).
4. Быстрее итерации для начинающего вайбкодера — один `npm run dev`, proxy на `:8000`.
5. Next.js имеет смысл позже для **tenant-facing portal** (родители детсада, клиенты консалтинга), где нужны публичные страницы и сложная маршрутизация.

**Предлагаемая структура репозитория:**

```
Flexity/
  backend/                 # существующий FastAPI
  platform-console/        # новый Vite + React (или admin/)
    src/
      api/                 # typed fetch client
      pages/               # Tenants, Templates, Audit...
      components/
```

**Стек Phase 1 (минимальный):**

- Vite + React + TypeScript
- React Router
- TanStack Query (кеш, refetch, loading states)
- shadcn/ui + Tailwind (быстрый admin UI, таблицы, формы)
- OpenAPI codegen опционально (`openapi-typescript`) — типы из `/openapi.json`

**Deploy:** статика на `console.flexity.asia` или `flexity.asia/console`, API на `flexity.asia/api/` (уже описано в `deploy/flexity-asia-nginx.md`).

**Не смешивать** Platform Console с будущим tenant UI — это разные приложения с разной auth-моделью и scope.

---

## Relevant files

### flexity_admin (reference only)

| Путь | Назначение |
|------|------------|
| `flexity_admin/AGENTS.md` | Vision platform owner (не совпадает с кодом) |
| `flexity_admin/app/__init__.py` | Flask app factory, blueprints |
| `flexity_admin/app/blueprints/` | Routes по модулям |
| `flexity_admin/app/services/user_access.py` | RBAC patterns |
| `flexity_admin/app/templates/` | 76 Jinja templates, role-based nav |
| `flexity_admin/docs/planning/TZ_CONSULTING_OS.md` | ТЗ Consulting OS |

### Flexity backend (Platform Console API)

| Путь | Назначение |
|------|------------|
| `backend/app/api/v1/router.py` | Регистрация всех routers |
| `backend/app/core/deps.py` | `get_current_user`, `require_provider_owner` |
| `backend/app/core/permissions.py` | Provider/tenant role checks |
| `backend/app/modules/auth/routes.py` | Login, register, refresh, me |
| `backend/app/modules/tenants/routes.py` | Tenant CRUD, memberships |
| `backend/app/modules/subscriptions/routes.py` | Plans, subscription assign |
| `backend/app/modules/module_registry/routes.py` | Registry + tenant modules |
| `backend/app/modules/industry_templates/routes.py` | Templates, apply, labels |
| `backend/app/modules/audit/routes.py` | Audit logs, security events |
| `backend/README.md` | curl examples, platform ops |
| `deploy/flexity-asia-nginx.md` | nginx `/api/` → :8005 |

### Flexity docs

| Путь | Назначение |
|------|------------|
| `docs/ai/PRODUCT_ARCHITECTURE.md` | Flexity = целевая платформа |
| `docs/ai/research/2026-06-03-flexity-initial-audit.md` | Backend phases 0–11 |

---

## Architecture classification

| Слой | Классификация |
|------|---------------|
| Platform Console UI | `platform_core` |
| flexity_admin Flask | `migration_map` / `research_only` (consulting_basic reference) |
| Tenant ERP screens | `universal_module` + `industry_template` (не Platform Console) |
| Новые backend endpoints для gaps | `platform_core` (требуют отдельный implementation plan) |

---

## Risks

| Риск | Описание | Митигация |
|------|----------|-----------|
| Путаница flexity_admin ↔ Platform Console | Разработка superadmin во Flask | Жёстко: только Flexity FastAPI + новый React |
| Два слоя entitlements | modules vs plan features | UI показывает оба; документировать в консоли |
| Bootstrap lock | Один provider company навсегда | Приемлемо для MVP; multi-provider — позже |
| Нет user invite API | Create tenant wizard ломается без owner | P0 backend endpoint до или вместе с UI |
| CORS / cookie auth | SPA на другом origin | JWT in memory + refresh; настроить CORS |
| Scope creep | Тащить CRM/finance из flexity_admin в консоль | Консоль = platform ops only |

---

## Constraints

- Не продолжать Flask как целевую платформу.
- Не писать код без явного approval и implementation plan.
- Не менять: auth architecture, tenant-логику, миграции, .env, production config — без отдельного согласования.
- flexity_admin не развивать как Platform Console — только reference для consulting_basic.
- Platform Console Phase 1 — минимальный scope: login, tenants, modules, subscriptions, templates (read), audit.

---

## Recommendation

### Phase 1 — Platform Console MVP (после approval)

**Backend (маленький пакет, отдельный plan):**
1. `GET /tenants/{id}/memberships`
2. `POST /auth/invite` или `POST /users` + assign membership (минимальный user management)
3. Опционально: `GET /platform/dashboard` aggregate

**Frontend (новая папка `platform-console/`):**
1. Vite + React + TypeScript + TanStack Query + shadcn/ui
2. Экраны: Login → Tenants list → Tenant detail (tabs: info, modules, subscription, labels, audit) → Create tenant wizard → Templates list → Security events
3. Deploy: static build + nginx рядом с API

**Не делать в Phase 1:**
- Plan CRUD, billing, impersonation, labels edit, template editor JSON
- Перенос CRM/finance экранов из flexity_admin

### Phase 2 (позже)

- Labels PATCH, subscription lifecycle, usage dashboard
- Provider staff roles (не только owner)
- Tenant-facing portal на Next.js (отдельное приложение)

---

## Do not touch

- `flexity_admin` production code (кроме read-only reference)
- Flexity auth/JWT схема без plan
- Alembic migrations без plan
- Trailers Flask
- Seed data планов/модулей без product decision
- `.env`, production nginx/systemd без live deploy plan

---

## Next safe step

1. **Получить approval** на этот brief.
2. Создать **implementation plan** (skill `implementation-plan`) с двумя треками:
   - Track A: 2–3 backend endpoints (memberships list, user invite)
   - Track B: scaffold `platform-console/` (Vite + React, login + tenants list)
3. Track B можно начать с read-only экранов на существующем API параллельно с Track A.
4. Проверка: `tests/test_mvp_scenario.py` + ручной smoke через новый UI.

---

## Open questions

1. Домен консоли: `console.flexity.asia` vs `flexity.asia/console`?
2. Нужен ли в Phase 1 drill-down в tenant data (parties, CRM) с `X-Tenant-ID`, или только platform metadata?
3. Создание tenant owner: invite по email или ручной UUID существующего user?
4. Нужен ли OpenAPI codegen с первого дня или достаточно ручных типов?
5. Когда планировать `consulting_basic` seed — до или после Platform Console?

---

## Final checks

- [x] No code changes
- [x] No migrations
- [x] No deploy
- [x] No destructive commands
- [x] flexity_admin проанализирован read-only
- [x] Flexity backend endpoints верифицированы по `routes.py`
- [x] Frontend recommendation зафиксирована
