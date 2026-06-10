# MVP Детского Сада в Flexity

**Дата:** 2026-06-03  
**Тип задачи:** industry template  
**Шаблон:** `kindergarten_basic`  
**Статус:** план утверждён, реализация ожидает approval по каждому этапу

---

## 1. Используемые модули Flexity

Все модули уже существуют в платформе. При применении шаблона `kindergarten_basic` они включаются автоматически:

| Модуль | Назначение в контексте детского сада |
|---|---|
| `parties` | Родители (guardian) и дети (enrollee) как контрагенты с custom fields |
| `crm` | Воронка поступления с 9 этапами |
| `catalog` | Абонементы и взносы как каталожные позиции |
| `documents` | Договор с родителем и заявление на зачисление |
| `finance` | Счета, оплаты, аллокация, дебиторка |
| `audit` | Платформенный аудит (включается автоматически, без отдельного модуля) |

---

## 2. Сущности детского сада и как они отображаются на Flexity

| Сущность детского сада | Модуль Flexity | Как реализуется |
|---|---|---|
| Ребёнок | `parties` | `party_type=person`, `party_role=enrollee` в `metadata_json` |
| Родитель / опекун | `parties` | `party_type=person`, `party_role=guardian` |
| Группа (Phase 1) | custom field | `group_name` — текстовое поле enrollee |
| Группа (Phase 2) | `parties` | Группа как party-организация с enrollee-участниками |
| Заявка на зачисление | `workflows.WorkItem` | `work_item_type=inquiry`, привязан к enrollee через `primary_party_id` |
| Этап воронки | `workflows.PipelineStage` | 9 предустановленных этапов в шаблоне |
| Договор с родителем | `documents.DocumentInstance` | Шаблон `parent_contract`, плейсхолдеры `{{ key }}` |
| Заявление | `documents.DocumentInstance` | Шаблон `enrollment_application` |
| Абонемент | `catalog.CatalogItem` | `item_type=subscription_service`, sku=`edu-monthly` |
| Регистрационный взнос | `catalog.CatalogItem` | `item_type=fee`, sku=`registration-fee` |
| Вступительный взнос | `catalog.CatalogItem` | `item_type=fee`, sku=`enrollment-fee` |
| Счёт | `finance.Invoice` | Привязан к `party_id` (родитель) и `work_item_id` |
| Оплата | `finance.Payment` | Метод: наличные / перевод / карта |
| Задолженность | `finance` | Через `/finance/receivables` и `/finance/summary` |

---

## 3. Что уже покрывает kindergarten_basic

Источник: `backend/app/modules/industry_templates/seed.py`  
Тела документов: `backend/app/modules/documents/service.py` → `_default_body_for_code()`

| Компонент | Содержание |
|---|---|
| Воронка поступления | 9 этапов: Новая заявка → Первичный контакт → Экскурсия → Ожидаем документы → Договор сформирован → Договор подписан → Оплата получена → Зачислен / Отказ |
| Custom fields enrollee | `birth_date` (required), `allergies`, `medical_notes`, `group_name` |
| Custom field work_item | `preferred_start_date` |
| DocumentTemplate | `parent_contract` — создаётся с телом через `_default_body_for_code()` |
| DocumentTemplate | `enrollment_application` — аналогично |
| Каталог | 3 позиции: абонемент/месяц, регистрационный взнос, вступительный взнос |
| AI-агенты (mock) | `ai_onboarding_manager`, `ai_document_manager` |
| Labels | Ребёнок, Родитель, Сотрудник, Заявка, Счёт, Оплата, Абонемент, Сбор |
| Роли | Администратор (tenant_owner), Заведующий (tenant_admin), Воспитатель (member) |

**Уже работающий сквозной сценарий (53 тест проходят):**

```
Tenant (kindergarten_basic)
  → apply_to_tenant → 5 модулей + воронка + doc templates + catalog + custom fields
  → parties: enrollee (ребёнок) + guardian (родитель)
  → WorkItem в воронке (move-stage по этапам)
  → generate_document (parent_contract с плейсхолдерами)
  → send_for_signature → upload_signed_file
  → Invoice (абонемент из catalog) → Payment → Allocation
  → /finance/receivables, /finance/summary
```

Покрыт тестом: `tests/test_mvp_scenario.py`

---

## 4. Чего не хватает

| # | Что отсутствует | Блокирует MVP | Комментарий |
|---|---|---|---|
| 1 | **Тела договоров** | Да | `_default_body_for_code()` даёт 4-строчный текст. Клиент не примет. Нужны полные тексты с реквизитами. |
| 2 | **Frontend / UI** | Да (для клиента) | Только API/Swagger. Администратор сада не может пользоваться системой без UI. |
| 3 | **Уведомления** | Да (для клиента) | Родители не получают счета, договоры, напоминания об оплате. |
| 4 | **Онлайн-оплата** | Нет (Phase 1) | Только ручная фиксация. Для MVP — допустимо. |
| 5 | **Авто-биллинг** | Нет (Phase 1) | Счета выставляются вручную каждый месяц. Для MVP — допустимо. |
| 6 | **Группы как сущность** | Нет (Phase 1) | `group_name` — текстовое поле. Нет вместимости, расписания, состава. |
| 7 | **Посещаемость** | Нет (Phase 1) | Не реализовано. За рамками MVP. |
| 8 | **PDF-рендеринг** | Нет (Phase 1) | Договор генерируется как `text/plain`. Нет форматированного PDF. |
| 9 | **Цены в каталоге** | Нет | `base_price` не задана в seed. Цены устанавливаются вручную через API. |
| 10 | **Tenant self-registration** | Нет | Детский сад регистрируется только через provider owner. |

---

## 5. Что можно сделать настройками template (без нового кода)

Только изменение в одном файле: `backend/app/modules/industry_templates/seed.py`

**Без миграций, без изменения кода, без риска для существующих тестов:**

1. Добавить `body_template` к элементам `default_document_templates` — тогда `import_templates_from_config()` будет использовать этот текст вместо минимального fallback из `_default_body_for_code()`.
2. Добавить `fields` к шаблонам документов — список переменных с метками для будущего UI.
3. Добавить custom field `guardian_relationship` (select: мать / отец / опекун) для `party_role=guardian`.
4. Добавить custom field `contract_start_date` для enrollee.
5. Добавить `base_price` и `currency` к catalog items.

**Важно:** изменения в seed вступают в силу только при следующем `apply_to_tenant` для нового tenant. Уже применённые tenant не затрагиваются.

---

## 6. Что требует нового кода

| Задача | Новые файлы | Сложность | Миграция |
|---|---|---|---|
| Модуль уведомлений (email/SMS) | `modules/notifications/` | Высокая | Да |
| PDF-рендеринг договора | `modules/documents/template_engine.py` + зависимость `weasyprint`/`reportlab` | Средняя | Нет |
| Frontend / UI | Отдельный проект (React/Next.js) | Очень высокая | Нет |
| Авто-биллинг | Background worker (Celery/ARQ) + scheduler | Высокая | Да |
| Группы как сущность | Новая модель в `parties` или отдельный модуль `groups` | Средняя | Да |
| Kaspi/Stripe онлайн-оплата | Провайдер в `integrations` + webhook | Высокая | Нет (новый provider) |

---

## 7. Вероятные файлы к изменению

### Этап 1 — Обогащение seed (1 файл, нет риска)

| Файл | Изменение |
|---|---|
| `backend/app/modules/industry_templates/seed.py` | Тела договоров, fields, guardian_relationship, base_price |

### Этап 2 — Документный движок (1–2 файла)

| Файл | Изменение |
|---|---|
| `backend/app/modules/documents/service.py` | Расширить `_default_body_for_code()`: более полный текст договора |
| `backend/tests/test_documents.py` | Обновить при изменении тел шаблонов (если тест проверяет содержимое) |

### Этап 3 — Уведомления (новый модуль, только после отдельного approval)

| Файл | Изменение |
|---|---|
| `backend/app/modules/notifications/` | Новый модуль: модели, сервис, роутер |
| `backend/app/api/v1/router.py` | Подключить роутер уведомлений |
| `backend/alembic/versions/YYYYMMDD_notifications.py` | Новая миграция |

---

## 8. Нужны ли миграции

| Этап | Миграция | Причина |
|---|---|---|
| Этап 1: обогащение seed | **Нет** | Все таблицы уже созданы в Phase 3–7. Seed применяется через API. |
| Этап 2: улучшение тел договоров | **Нет** | `body_template` — уже существующее поле `Text` в `document_templates`. |
| Этап 3: уведомления | **Да** | Нужны новые таблицы: `notification_templates`, `notification_queue`. |
| Этап 4: авто-биллинг | **Да** | Нужны таблицы: `recurring_invoices`, `billing_schedule`. |
| Этап 5: группы | **Да** | Новая модель или таблица для групп с составом. |

---

## 9. Риски

| # | Риск | Уровень | Описание |
|---|---|---|---|
| 1 | **Нет frontend** | Критический | Администратор сада не может пользоваться системой. Swagger — только для разработки. |
| 2 | **Договоры — минимальный текст** | Высокий | `parent_contract` содержит 4 строки. Клиент не подпишет такой договор. |
| 3 | **Движок документов — только text/plain** | Средний | Нет PDF. Договор нельзя распечатать в нормальном виде без дополнительной обработки. |
| 4 | **Нет уведомлений** | Средний | Родители не получат ни одного сообщения. Работа только через личный контакт администратора. |
| 5 | **Seed — только для новых tenant** | Низкий | Обновление seed не меняет уже применённые шаблоны. Для повторного применения нужен новый tenant или ручное обновление через API. |
| 6 | **Обратная совместимость seed** | Низкий | `import_templates_from_config` пропускает уже существующие шаблоны (`if repo.get_template_by_code(...): continue`). Изменения в seed безопасны для существующих tenant. |
| 7 | **AI — только mock** | Низкий | `ai_onboarding_manager` не выполняет реальных действий. Для MVP — допустимо. |

---

## 10. Первый маленький шаг

**Цель:** обогатить шаблон `kindergarten_basic` реалистичными данными.

**Файл:** `backend/app/modules/industry_templates/seed.py`  
**Размер изменения:** 1 файл, ~80–120 строк добавок  
**Риск:** минимальный

**Что добавить:**

```
default_document_templates:
  - parent_contract:
      body_template: полный текст договора с плейсхолдерами
      fields: contract_number, child_name, guardian_name, guardian_relationship,
              contract_date, monthly_fee, start_date, kindergarten_name
  - enrollment_application:
      body_template: полный текст заявления
      fields: child_name, birth_date, guardian_name, application_date, group_name

default_custom_fields (добавить):
  - entity_type: party, party_role: guardian
    field_key: guardian_relationship
    field_type: select
    label: Тип представителя
    options: мать / отец / законный опекун

  - entity_type: party, party_role: enrollee
    field_key: contract_start_date
    field_type: date
    label: Дата начала посещения

default_catalog_items (обновить):
  - edu-monthly: base_price: 25000, currency: KZT
  - registration-fee: base_price: 5000, currency: KZT
  - enrollment-fee: base_price: 10000, currency: KZT
```

**Почему безопасно:**
- Только seed-данные, логика не меняется
- Применяется только при следующем `apply_to_tenant`
- Существующие tenant не затронуты
- Тесты не нужно менять
- Нет миграций

**Проверка:** после изменения запустить `pytest --tb=short -q` — все 53 теста должны остаться зелёными.

---

## Порядок реализации (по этапам)

| Этап | Содержание | Файлы | Требует approval |
|---|---|---|---|
| **1** | Обогатить seed: договоры, custom fields, цены | `seed.py` (1 файл) | Да |
| **2** | Улучшить тела договоров в `_default_body_for_code` | `documents/service.py` | Да |
| **3** | Research brief для модуля уведомлений | `docs/ai/research/` | Нет (только doc) |
| **4** | Реализовать notifications модуль (email) | новый модуль + миграция | Да (отдельно) |
| **5** | Решить вопрос frontend | отдельное решение | Да (отдельно) |
