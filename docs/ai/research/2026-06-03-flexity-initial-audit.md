# Первичный аудит Flexity

**Дата:** 2026-06-03  
**Тип задачи:** platform core / legacy/reference analysis  
**Статус:** research only, код не изменялся

---

## 1. Стек проекта

| Компонент | Технология |
|---|---|
| Backend | Python 3.12, FastAPI ≥ 0.115 |
| ORM | SQLAlchemy 2.0 |
| Миграции | Alembic ≥ 1.14 |
| База данных | PostgreSQL 16 |
| Auth | JWT (python-jose) + bcrypt |
| Валидация | Pydantic v2 |
| Деплой | Docker Compose, systemd |
| Тесты | pytest, pytest-asyncio, httpx (in-memory SQLite) |
| Lint | ruff |
| Frontend | **отсутствует** (в MVP не входит) |
| Background workers | **отсутствуют** (Celery запланирован, не реализован) |
| Реальные интеграции | **отсутствуют** (только mock Bitrix24) |

Staging: `flexity.asia:8005` (`/api/` проксируется nginx).  
Production: `flexity.kz` — запланирован, не развёрнут.

---

## 2. Фактически реализованные модули

Реализованы все 11 фаз backend (фазы 0–11). Все миграции датированы 2025-06-01.  
Точка входа роутера: `backend/app/api/v1/router.py`.

### Зарегистрированные модули (module_registry/seed.py)

- `parties` — контрагенты и организации
- `crm` — пайплайны, сделки, задачи (зависит от `parties`)
- `catalog` — номенклатура, прайс-листы
- `documents` — шаблоны, генерация, подпись
- `finance` — счета, оплаты, аллокация
- `accounting` — юрлица, налоговые профили
- `integrations` — внешние системы
- `ai` — агенты, задачи, предложения

### Тарифные планы (subscriptions/seed.py)

| Тариф | Модули | Ключевые features |
|---|---|---|
| `starter` | parties, crm | work_items.create/read |
| `business` | parties, crm, catalog, documents, finance | + documents.generate, finance.invoices.create, catalog.items.create |
| `enterprise` | все 8 модулей | все features + ai.tasks.create |

---

## 3. Таблица модулей: план vs факт

| Модуль | Статус | Ключевые файлы | Что реализовано | Чего не хватает | Приоритет |
|---|---|---|---|---|---|
| auth | ✅ Есть | `modules/auth/` | register, login, JWT refresh, /me | 2FA, email-верификация | Низкий |
| tenants | ✅ Есть | `modules/tenants/` | CRUD, статусы, plan_code, industry_template | Self-registration | Низкий |
| provider | ✅ Есть | `modules/provider/` | provider company + 8 ролей | — | Низкий |
| module_registry | ✅ Есть | `modules/module_registry/` | 8 модулей, enable/disable, зависимости, external mode | — | Низкий |
| subscriptions | ✅ Есть | `modules/subscriptions/` | 3 тарифа, features, usage limits, entitlements | Реальный биллинг, оплата подписки | Средний |
| industry_templates | ✅ Есть | `modules/industry_templates/` | CRUD шаблонов, apply_to_tenant, labels, kindergarten_basic | consulting_basic seed | Средний |
| parties | ✅ Есть | `modules/parties/` | person/org/SP, custom fields, contacts, адреса | — | Низкий |
| workflows / crm | ✅ Есть | `modules/workflows/` | pipelines, stages, work items, activities, tasks, reminders, move-stage | — | Низкий |
| catalog | ✅ Есть | `modules/catalog/` | items, units, price lists | — | Низкий |
| documents | ✅ Есть | `modules/documents/` | шаблоны, генерация, send_for_signature (заглушка), upload signed, file storage | Реальная ЭП, email отправка | **Высокий** (кг) |
| finance | ✅ Есть | `modules/finance/` | Invoice, Payment, PaymentAllocation, receivables, summary | Повторяющиеся счета, online-оплата | **Высокий** (кг) |
| accounting | ✅ Есть | `modules/accounting/` | legal_entities, tax_profiles | Реальный расчёт налогов (tax_amount=0) | Низкий (MVP) |
| integrations | ⚠️ Частично | `modules/integrations/` | providers, connections, sync jobs, external refs, mock Bitrix24 | Реальный Bitrix24, банки, email | Средний |
| ai | ⚠️ Частично | `modules/ai/` | agents, tasks (mock), proposals, approve/execute, usage | Реальный LLM, оркестратор | Средний |
| audit | ✅ Есть | `modules/audit/` | AuditLog, SecurityEvent, DataAccessLog, middleware | Полное покрытие всех действий | Низкий |
| HR | ❌ Нет | — | — | Сотрудники, должности | Будущее |
| payroll | ❌ Нет | — | — | Расчёт зарплат | Будущее |
| inventory | ❌ Нет | — | — | Склад, остатки | Будущее (trailers) |
| production | ❌ Нет | — | — | BOM, производственные маршруты | Будущее (trailers) |
| sales | ❌ Нет | — | — | Заказы, отгрузки | Будущее |
| tax | ❌ Заглушка | — | tax_amount = 0 везде | Реальный НДС/КПН | Будущее |
| data_quality | ❌ Нет | — | — | Правила, дубликаты | Будущее |
| learning | ❌ Нет | — | — | Обучение и допуск персонала | Будущее |
| notifications | ❌ Нет | — | — | Email, SMS, Telegram родителям | **Критично для кг** |

---

## 4. Оценка kindergarten_basic как первого подписочного template

### Что уже сконфигурировано в шаблоне

Файл: `backend/app/modules/industry_templates/seed.py`

| Конфигурация | Содержание |
|---|---|
| Воронка поступления | 9 этапов: Новая заявка → Первичный контакт → Экскурсия → Ожидаем документы → Договор сформирован → Договор подписан → Оплата получена → Зачислен / Отказ |
| Custom fields (ребёнок) | birth_date (required), allergies, medical_notes, group_name |
| Custom fields (work_item) | preferred_start_date |
| Шаблоны документов | parent_contract (Договор с законным представителем), enrollment_application (Заявление на зачисление) |
| Каталог | Обучение/месяц (subscription_service), Регистрационный взнос (fee), Вступительный взнос (fee) |
| AI агенты | ai_onboarding_manager, ai_document_manager (mock) |
| Labels | Ребёнок, Родитель, Сотрудник, Заявка, Счёт, Оплата, Абонемент, Сбор |
| Роли | Администратор (tenant_owner), Заведующий (tenant_admin), Воспитатель (member) |
| Тарифные модули | parties, crm, documents, finance, catalog |

### Вывод

`kindergarten_basic` **может быть применён как первый tenant прямо сейчас** для ручного сценария через API:

1. Provider owner создаёт tenant с `industry_template_code: kindergarten_basic`.
2. Автоматически включаются 5 модулей, создаётся воронка, custom fields, шаблоны документов, каталог.
3. Можно вести родителей и детей как parties.
4. Можно запускать заявки по воронке поступления.
5. Можно генерировать договор и заявление.
6. Можно выставлять счета и фиксировать оплаты.

Сценарий покрыт тестом: `tests/test_mvp_scenario.py`.

---

## 5. Чего не хватает для MVP детского сада

Ниже — минимально необходимое для реального коммерческого использования (не для demo/PoC).

| # | Что не хватает | Причина критичности |
|---|---|---|
| 1 | **Frontend / UI** | Без интерфейса клиент не может использовать систему. Всё работает только через API/Swagger. |
| 2 | **Уведомления (email/SMS/Telegram)** | Родители не получают счета, договоры, напоминания об оплате. |
| 3 | **Онлайн-оплата** | Нет Kaspi Pay, Stripe, банковского эквайринга. Оплата фиксируется только вручную администратором. |
| 4 | **Реальная ЭП / подпись договора** | `send_for_signature` — заглушка. Договор нельзя подписать онлайн. |
| 5 | **Автоматические повторяющиеся счета** | Ежемесячный абонемент нужно выставлять вручную каждый месяц. Нет авто-биллинга. |
| 6 | **Группы как отдельная сущность** | Сейчас group_name — только текстовое поле. Нет модели группы, вместимости, расписания, состава. |
| 7 | **Посещаемость и расписание** | Не реализованы. |
| 8 | **Tenant self-registration** | Детский сад не может самостоятельно зарегистрироваться. Tenant создаётся только provider owner'ом. |
| 9 | **Бизнес-отчёты** | Нет отчётов: дебиторка по группам, поступления за месяц, ожидаемые оплаты. Базовый `/finance/summary` есть. |

---

## 6. Риски перед началом разработки

| # | Риск | Уровень | Описание |
|---|---|---|---|
| 1 | **Нет frontend** | 🔴 Критический | Весь MVP — только REST API. Любой реальный пользователь требует UI. |
| 2 | **Все миграции созданы одним днём** | 🟡 Средний | Все 11 файлов датированы 2025-06-01 — возможно, scaffold. Нужно запустить тесты и проверить работоспособность. |
| 3 | **AI — полностью mock** | 🟡 Средний | Все задачи выполняются с `run_mock=True`. Реального LLM нет. AI-агенты детского сада не выполняют реальных действий. |
| 4 | **ЭП — заглушка** | 🟡 Средний | `send_for_signature` не делает ничего реального. Родитель не может подписать договор онлайн. |
| 5 | **Нет уведомлений** | 🟡 Средний | Ни email, ни SMS. Родители не получат ни одного сообщения от системы. |
| 6 | **Нет фоновых задач** | 🟡 Средний | Без Celery/ARQ нет авто-биллинга, напоминаний, отложенной синхронизации. |
| 7 | **Документный движок** | 🟡 Средний | `modules/documents/template_engine.py` вероятно использует простую замену строк. Нет Jinja2, нет PDF-рендеринга. |
| 8 | **RBAC — базовый** | 🟢 Низкий | 3 роли tenant (owner/admin/member), нет fine-grained permissions на уровне объектов. |
| 9 | **Нет self-onboarding** | 🟢 Низкий | Tenant создаётся только провайдером. Нет публичного signup flow. |
| 10 | **Нет мониторинга** | 🟢 Низкий | Нет Sentry, Prometheus, структурированного логирования для продакшена. |
| 11 | **industry_trailers** | 🟢 Информационный | Trailers Flask — legacy reference-проект. Разработка industry_trailers package во Flexity начнётся только после карты миграции. Не блокирует kindergarten_basic. |

---

## 7. Следующий маленький шаг

**Цель:** убедиться, что платформа реально работает и все 11 фаз проходят тесты.

### Команды

```bash
cd backend

# Установить зависимости (если не установлены)
pip install -e ".[dev]"

# Запустить все тесты
pytest --tb=short -q

# Запустить только сквозной сценарий MVP
pytest tests/test_mvp_scenario.py -v
```

### Что покажут тесты

- Проходят ли все 11 фаз (auth, tenants, parties, workflows, catalog, documents, finance, accounting, integrations, ai, audit).
- Работает ли применение шаблона `kindergarten_basic` end-to-end.
- Есть ли сломанные тесты, требующие внимания до начала разработки.

### После получения результатов тестов

Можно уверенно планировать первый шаг разработки. Рекомендуемый порядок согласно `PRODUCT_ARCHITECTURE.md`:

1. Стабилизировать платформу (тесты зелёные).
2. Сделать kindergarten_basic первым коммерческим tenant — начать с уведомлений или frontend.
3. Consulting_basic — второй template.
4. Industry_trailers — только после карты миграции Trailers Flask.
