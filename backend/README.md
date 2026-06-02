# CoreOps Platform — Backend

Модульное multi-tenant SaaS-ядро на FastAPI.

## Требования

- Python 3.12+
- Docker и Docker Compose (для локальной БД)
- PostgreSQL 16 (через Docker или локально)

## Быстрый старт

### Docker Compose (рекомендуется)

```bash
cd backend
cp .env.example .env
docker compose up --build
```

API: http://localhost:8000  
Документация: http://localhost:8000/docs  
Health: http://localhost:8000/api/v1/health

### Локально без Docker API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
# Запустите PostgreSQL и укажите DATABASE_URL в .env
uvicorn app.main:app --reload
```

## Миграции (Alembic)

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Миграции

```bash
alembic upgrade head
```

При первом запуске API сидятся модули, тарифы и фичи (`SEED_ON_STARTUP=true` по умолчанию).

### Модули и тарифы (Phase 2)

```bash
# Реестр модулей
curl http://localhost:8000/api/v1/modules/registry -H "Authorization: Bearer <token>"

# Модули tenant
curl http://localhost:8000/api/v1/tenants/<tenant_id>/modules -H "Authorization: Bearer <token>"

# Включить модуль (с проверкой зависимостей)
curl -X POST http://localhost:8000/api/v1/tenants/<tenant_id>/modules/parties/enable -H "Authorization: Bearer <token>"
curl -X POST http://localhost:8000/api/v1/tenants/<tenant_id>/modules/crm/enable -H "Authorization: Bearer <token>"

# Режим external (например Bitrix24)
curl -X PATCH http://localhost:8000/api/v1/tenants/<tenant_id>/modules/crm/mode \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"mode":"external","external_provider_code":"bitrix24"}'

# Назначить тариф
curl -X POST http://localhost:8000/api/v1/tenants/<tenant_id>/subscription \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"plan_code":"business"}'

# Тарифы платформы
curl http://localhost:8000/api/v1/plans -H "Authorization: Bearer <token>"
```

Guard для endpoint-ов:

```python
from app.core.modules import require_module
from app.core.entitlements import require_feature

@router.get("/items")
def list_items(ctx: TenantContext = Depends(require_module("crm"))):
    ...
```

### Industry Templates (Phase 3)

```bash
# Список шаблонов (включая kindergarten_basic)
curl http://localhost:8000/api/v1/industry-templates -H "Authorization: Bearer <token>"

# Применить шаблон к tenant
curl -X POST http://localhost:8000/api/v1/tenants/<tenant_id>/apply-template/<template_id> \
  -H "Authorization: Bearer <token>"

# Или при создании tenant
curl -X POST http://localhost:8000/api/v1/tenants \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Садик","slug":"garden","industry_template_code":"kindergarten_basic"}'

# UI-лейблы tenant
curl http://localhost:8000/api/v1/tenants/<tenant_id>/labels -H "Authorization: Bearer <token>"

# Воронки (после применения шаблона, нужен X-Tenant-ID и модуль crm)
curl http://localhost:8000/api/v1/pipelines -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant_id>"
```

Шаблон `kindergarten_basic` — **только данные конфигурации**, без отдельного кода под отрасль.

### Parties (Phase 4)

Все запросы требуют `Authorization` и заголовок `X-Tenant-ID`, модуль `parties` должен быть включён.

```bash
# Список контрагентов
curl http://localhost:8000/api/v1/parties -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant_id>"

# Создать контрагента с custom fields
curl -X POST http://localhost:8000/api/v1/parties \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "party_type": "person",
    "display_name": "Иван Петров",
    "party_role": "enrollee",
    "custom_fields": {"birth_date": "2020-05-15", "allergies": "нет", "group_name": "Солнышко"},
    "contact_methods": [{"method_type": "email", "value": "parent@example.com", "is_primary": true}]
  }'

# Определения custom fields для tenant
curl http://localhost:8000/api/v1/parties/custom-field-definitions \
  -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant_id>"
```

Типы party: `person`, `organization`, `sole_proprietor`. Роль (`party_role`) хранится в `metadata_json` и фильтрует применимые custom fields.

### Workflows / CRM (Phase 5)

Требуются `X-Tenant-ID`, включённый модуль `crm` и feature `crm.work_items.create` (тариф business+).

```bash
# Воронки
curl http://localhost:8000/api/v1/pipelines -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant_id>"

# Work item (универсальная сущность: заявка, запись, сделка…)
curl -X POST http://localhost:8000/api/v1/work-items \
  -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{"pipeline_id":"<uuid>","work_item_type":"inquiry","title":"Новая заявка"}'

# Перемещение по воронке
curl -X POST http://localhost:8000/api/v1/work-items/<id>/move-stage \
  -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{"stage_id":"<stage_uuid>"}'

# Активность и задача
curl -X POST http://localhost:8000/api/v1/work-items/<id>/activities -H "..." -d '{"title":"Звонок"}'
curl -X POST http://localhost:8000/api/v1/work-items/<id>/tasks -H "..." -d '{"title":"Подготовить договор"}'
```

Фильтры списка: `pipeline_id`, `stage_id`, `status`, `work_item_type`, `search`.

### Catalog (Phase 6)

Требуются `X-Tenant-ID`, модуль `catalog`, для создания — feature `catalog.items.create`.

```bash
# Единицы измерения
curl -X POST http://localhost:8000/api/v1/catalog/units -H "..." -d '{"code":"month","name":"Месяц"}'

# Товары и услуги
curl http://localhost:8000/api/v1/catalog/items -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant_id>"
curl -X POST http://localhost:8000/api/v1/catalog/items -H "..." \
  -d '{"item_type":"service","name":"Консультация","base_price":"5000","currency":"RUB"}'

# Прайс-лист
curl -X POST http://localhost:8000/api/v1/catalog/price-lists -H "..." \
  -d '{"code":"default","name":"Основной","currency":"RUB"}'
curl -X POST http://localhost:8000/api/v1/catalog/price-lists/<pl_id>/items -H "..." \
  -d '{"catalog_item_id":"<item_id>","price":"4500"}'
```

Типы: `product`, `service`, `subscription_service`, `bundle`, `fee`, `discount`.

### Documents (Phase 7)

Требуются `X-Tenant-ID`, модуль `documents`, для генерации — feature `documents.generate`.
При применении industry template (`kindergarten_basic`) создаются шаблоны `parent_contract` и `enrollment_application`.
Файлы сохраняются локально в `STORAGE_PATH` (по умолчанию `./storage`).

```bash
curl http://localhost:8000/api/v1/document-templates -H "Authorization: Bearer <token>" -H "X-Tenant-ID: <tenant_id>"

curl -X POST http://localhost:8000/api/v1/documents/generate -H "..." \
  -d '{"template_id":"<id>","context":{"contract_number":"1","guardian_name":"Иванова","child_name":"Пётр","contract_date":"2025-09-01"}}'

curl -X POST http://localhost:8000/api/v1/documents/<doc_id>/send-for-signature -H "..."

curl -X POST http://localhost:8000/api/v1/documents/<doc_id>/upload-signed-file -H "..." \
  -F "file=@signed.pdf"
```

### Finance (Phase 8)

Модуль `finance`, создание счетов — feature `finance.invoices.create`. Налоги на MVP не рассчитываются (`tax_amount = 0`).

```bash
curl -X POST http://localhost:8000/api/v1/finance/invoices -H "..." \
  -d '{"party_id":"<uuid>","lines":[{"description":"Обучение","quantity":"1","unit_price":"15000"}],"issue":true}'

curl -X POST http://localhost:8000/api/v1/finance/payments -H "..." \
  -d '{"party_id":"<uuid>","amount":"15000","payment_date":"2025-09-15","method":"bank_transfer"}'

curl -X POST http://localhost:8000/api/v1/finance/payments/<payment_id>/allocate -H "..." \
  -d '{"allocations":[{"invoice_id":"<uuid>","amount":"15000"}]}'

curl http://localhost:8000/api/v1/finance/receivables -H "..."
curl http://localhost:8000/api/v1/finance/summary -H "..."
```

### Accounting (Phase 8)

Модуль `accounting` (тариф Enterprise по умолчанию): юрлица и налоговые профили без расчёта налогов.

```bash
curl -X POST http://localhost:8000/api/v1/accounting/legal-entities -H "..." \
  -d '{"name":"ООО Ромашка","country":"RU","tax_number":"7700000000"}'
curl -X POST http://localhost:8000/api/v1/accounting/tax-profiles -H "..." \
  -d '{"legal_entity_id":"<uuid>","code":"ru_general","name":"ОСН","tax_regime":"general"}'
```

### Integrations (Phase 9)

Модуль `integrations`. Mock Bitrix24 — без реального API. Режим `external` для CRM требует активное подключение.

```bash
curl http://localhost:8000/api/v1/integrations/providers -H "Authorization: Bearer <token>"

curl -X POST http://localhost:8000/api/v1/integrations/connections -H "..." -H "X-Tenant-ID: <id>" \
  -d '{"provider_code":"bitrix24","module_code":"crm","name":"Bitrix CRM","credentials_json":{"portal_url":"https://demo.bitrix24.ru"}}'

curl -X POST http://localhost:8000/api/v1/integrations/connections/<id>/test -H "..."
curl -X POST http://localhost:8000/api/v1/integrations/connections/<id>/sync -H "..."
curl http://localhost:8000/api/v1/integrations/sync-jobs -H "..."
curl http://localhost:8000/api/v1/integrations/external-references -H "..."

# External CRM mode
curl -X PATCH http://localhost:8000/api/v1/tenants/<tenant_id>/modules/crm/mode -H "..." \
  -d '{"mode":"external","external_provider_code":"bitrix24"}'
```

### AI Foundation (Phase 10)

Модуль `ai`, задачи — feature `ai.tasks.create`. Критичные действия (`send_document`, `create_invoice`, …) **нельзя выполнить без approve**.

```bash
curl http://localhost:8000/api/v1/ai/agents -H "..." -H "X-Tenant-ID: <id>"
curl -X POST http://localhost:8000/api/v1/ai/tasks -H "..." \
  -d '{"agent_id":"<uuid>","title":"Проверить заявку","task_type":"enrollment","run_mock":true}'
curl http://localhost:8000/api/v1/ai/action-proposals?status=pending -H "..."
curl -X POST http://localhost:8000/api/v1/ai/action-proposals/<id>/approve -H "..."
curl -X POST http://localhost:8000/api/v1/ai/action-proposals/<id>/execute -H "..."
curl http://localhost:8000/api/v1/ai/usage/summary -H "..."
```

### Audit (Phase 11)

Платформенный аудит (не требует отдельного модуля). Чтение: provider staff или tenant owner/admin.

```bash
curl http://localhost:8000/api/v1/audit/security-events -H "Authorization: Bearer <token>"
curl "http://localhost:8000/api/v1/audit/logs?tenant_id=<uuid>" -H "Authorization: Bearer <token>"
curl http://localhost:8000/api/v1/audit/data-access -H "..." -H "X-Tenant-ID: <tenant_id>"
```

Автоматически пишутся: login/register/refresh, чтение party, approve/reject/execute AI proposal.

### Auth (Phase 1)

```bash
# Первый provider owner (только пока нет пользователей)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"securepass123","full_name":"Owner","company_name":"My Firm","company_slug":"my-firm"}'

# Вход
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"securepass123"}'

# Профиль
curl http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer <access_token>"
```

### Tenants (Phase 1)

Provider owner может создавать tenants:

```bash
curl -X POST http://localhost:8000/api/v1/tenants \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Client A","slug":"client-a","plan_code":"starter"}'
```

### Modules & Entitlements (Phase 2)

```bash
# Реестр модулей
curl http://localhost:8000/api/v1/modules/registry -H "Authorization: Bearer <token>"

# Модули tenant
curl http://localhost:8000/api/v1/tenants/<tenant_id>/modules -H "Authorization: Bearer <token>"

# Включить модуль (с проверкой зависимостей)
curl -X POST http://localhost:8000/api/v1/tenants/<tenant_id>/modules/parties/enable -H "Authorization: Bearer <token>"
curl -X POST http://localhost:8000/api/v1/tenants/<tenant_id>/modules/crm/enable -H "Authorization: Bearer <token>"

# Режим external (например Bitrix24)
curl -X PATCH http://localhost:8000/api/v1/tenants/<tenant_id>/modules/crm/mode \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"mode":"external","external_provider_code":"bitrix24"}'

# Тарифы и подписка
curl http://localhost:8000/api/v1/plans -H "Authorization: Bearer <token>"
curl -X POST http://localhost:8000/api/v1/tenants/<tenant_id>/subscription \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"plan_code":"business"}'
```

В коде endpoint-ов Phase 3+:

```python
@router.post("/work-items", dependencies=[Depends(require_module("crm"))])
# или
def create(..., ctx: TenantContext = Depends(require_feature("crm.work_items.create"))):
    ...
```

## Тесты

```bash
pytest
```

Сквозной сценарий MVP (Definition of Done из ТЗ):

```bash
pytest tests/test_mvp_scenario.py -v
```

Ручной smoke при запущенном API:

```bash
python scripts/mvp_smoke.py
```

Без запущенной БД health вернёт `status: degraded` и `database: unavailable` — это ожидаемо.

## Структура

```
app/
  main.py              # FastAPI application
  core/                # config, database, deps, exceptions
  api/v1/              # HTTP routers (health, …)
  modules/             # business modules (Phase 1+)
alembic/               # migrations
tests/                 # pytest
```

## Фазы разработки

| Phase | Содержание |
|-------|------------|
| 0 | Bootstrap |
| 1 | Auth + Tenant + Provider |
| 2 | Module Registry + Entitlements |
| 3 | Industry Templates |
| 4 | Parties + Custom Fields |
| 5 | Workflows / CRM |
| 6 | Catalog |
| 7 | Documents (шаблоны, генерация, подпись, audit) |
| 8 | Finance + Accounting (счета, оплаты, дебиторка, legal entity) |
| 9 | Integrations (providers, connections, sync, external refs, mock Bitrix) |
| 10 | AI Foundation (agents, tasks, proposals, approval, usage) |
| 11 | Audit (AuditLog, DataAccessLog, SecurityEvent) |
| … | См. ТЗ |
