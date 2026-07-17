# Flexity Booking — продуктовая концепция

## 1. Позиционирование

**Flexity Booking** — отраслевой модуль платформы Flexity для бронирования территорий, объектов и распределённой недвижимости с разными владельцами.

Это **не** отдельный бренд, не одноразовый сервис под одного клиента и не standalone-приложение. Booking живёт внутри tenant workspace Flexity: те же пользователи, роли, оплаты, документы и audit, что и в остальной ERP.

**Industry package** Flexity (`booking` / `booking_basic`), потому что нужна доменная логика: карта территории, календарь доступности, удержание слота, права владельцев, комиссии, внешние каналы.

```
Flexity Core
  → универсальные модули (parties, finance, documents, workflows, …)
  → industry template / industry package
  → tenant customization (будущий слой)
  → Flexity Booking (industry package)
```

## 2. Для кого продукт

| Актор | Роль в Booking |
|--------|----------------|
| **Оператор территории** | Tenant Flexity; владеет схемой, правилами бронирования, каналами |
| **Владелец объекта** | Party + `owner`; получает выплату/комиссию, видит свои объекты |
| **Администратор / диспетчер** | User с `management_permissions`; подтверждает бронь, Telegram |
| **Гость (клиент)** | Party-клиент; бронирует через публичную mobile web без аккаунта |
| **Платформа Flexity** | Provider; тариф модуля, audit, будущий маркетплейс |

Сценарии: базы отдыха, глэмпинг, кемпинг, фермы с несколькими домиками, коворкинг-зоны, аренда залов, распределённая недвижимость с разными собственниками на одной карте.

## 3. Ключевые сущности (концептуально)

### 3.1 Территория (`territory`)

Единый контур бронирования: границы, **часовой пояс**, правила (минимальное число ночей, сезонные коэффициенты, deposit). На MVP — **одна** активная territory на tenant; модель допускает **N** территорий и **кросс-tenant** каталог в будущем.

### 3.2 Объект (`bookable_object`)

Минимальная единица брони: домик, зона, беседка, зал. Связан с **владельцем**, точкой на **map**, фото, собственным **check-in/out** и ценой. Групповое бронирование = несколько items в одном `booking_order`.

### 3.3 Владелец (`owner`)

Extension поверх **parties** (person/org). Несколько owners на территории; один owner — объекты в **разных** территориях (post-MVP). Комиссия платформы задаётся в `commissions`.

### 3.4 Права управления (`management_permissions`)

Granular ACL: объект / территория / owner scope. Роли Flexity RBAC не заменяют — дополняют (например «только Telegram-алерты» без финансов в админке).

## 4. Каналы и интерфейсы

### 4.1 Клиентская mobile web

Публичная **mobile-first** страница территории:

- схема / список объектов;
- календарь доступности;
- корзина из нескольких объектов;
- выбор дат заезда/выезда **по объекту**;
- таймер **удержания 30 мин** после выбора слота;
- контактные данные → создание **party**;
- оплата MVP: реквизиты + **ручное** подтверждение оператором.

Без отдельного приложения; маршрут Flexity (`/{tenant}/book/{territory}`) или поддомен tenant.

### 4.2 Telegram-бот (админы и владельцы)

- новая бронь, отмена, подтверждение оплаты;
- напоминание о незавершённой брони до истечения hold;
- дайджест по объектам owner.

На MVP — исходящие **уведомления**, не полноценный conversational bot.

Интеграция через модуль **integrations** + очередь уведомлений Booking.

### 4.3 WhatsApp

Канал **коммуникации** с клиентом и оператором:

- MVP: **ссылка** `wa.me/...` на публичной странице и в подтверждении брони;
- post-MVP: WhatsApp Business API через `external_channels`.

Без WhatsApp API в MVP — только deep link, без автоматических исходящих через Meta.

### 4.4 2GIS

Канал **входа по ссылке**:

- в карточке 2GIS — ссылка на публичную booking page territory;
- UTM/referrer `source=2gis` в `booking_orders.source` для аналитики;
- без API-интеграции 2GIS в MVP.

2GIS — discovery и traffic, не система бронирования.

### 4.5 Админка (tenant workspace)

Web UI внутри Flexity:

- редактор карты и объектов;
- календарь броней;
- ручное **approve** оплаты;
- настройка hold, timezone, commission;
- привязка owners и прав;
- просмотр audit.

## 5. Эволюция продукта

| Фаза | Содержание |
|-------|------------|
| **MVP** | 1 territory, карта, multi-object бронь, hold 30 min, manual payment, Telegram ops, WhatsApp link, 2GIS link |
| **Growth** | N территорий, owner портфель, отчёты, WhatsApp API |
| **Marketplace** *(future, не MVP)* | Общий каталог Flexity: поиск, рейтинг, cross-tenant discovery |
| **External sync** *(future)* | API/channel adapters (OTA, aggregators), двусторонний sync |

## 6. Каталог / маркетплейс (future, не MVP)

Публичный индекс территорий и объектов **нескольких** tenants:

- единый поиск по региону;
- фильтры: тип объекта, цена, даты;
- комиссия платформы через `commissions`;
- opt-in/opt-out листинга.

Каталог опирается на **catalog** Flexity, а не дублирует card в silo. **Не входит в MVP.**

## 7. Внешние каналы (future `external_channels`)

Abstraction для:

- inbound webhook (channel создаёт/отменяет бронь);
- outbound sync availability;
- idempotency + mapping на `booking_orders`.

OTA, WhatsApp API, агрегаторы — **адаптеры**, не форк core. **Не входят в MVP.**

## 8. Принципы архитектуры

1. **Reuse core** — clients → parties; счёт/оплата → finance; задачи → workflows; события → audit.
2. **Tenant boundary** — данные territory изолированы `tenant_id`; кросс-tenant только через marketplace contract.
3. **Time correctness** — timestamps в UTC; business/UI timezone из territory; check-in/out — local time territory.
4. **Availability as domain** — расчёт слотов в Booking service, не в CRM.
5. **No second CRM** — статусы брони в Booking; optional mirror `work_item`.
6. **No duplicate finance** — `booking_orders` доменные; invoices/payments — finance module.

## 9. Соседство с другими отраслями Flexity

| Модуль | Пересечение |
|--------|-------------|
| kindergarten_basic | Другой domain; общие parties/finance |
| consulting_basic | Тот же payment rail |
| clinic_basic | UX-паттерны слотов, не модели |
| industry_trailers | Reference для reservation / availability |

## 10. Что сознательно не входит в концепцию

- отдельный бренд;
- отдельная БД или auth;
- микросервис бронирования на MVP;
- online-acquiring в MVP;
- marketplace в MVP;
- WhatsApp API в MVP;
- tenant customization layer в коде до CR approval.

## 11. Связанные документы

- [README.md](./README.md)
- [MVP_SCOPE.md](./MVP_SCOPE.md)
- [DATA_MODEL.md](./DATA_MODEL.md)
- [FLEXITY_INTEGRATION.md](./FLEXITY_INTEGRATION.md)
- [IMPLEMENTATION_PLAN_E1.md](./IMPLEMENTATION_PLAN_E1.md)
