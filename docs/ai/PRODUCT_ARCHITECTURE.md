# Flexity Product Architecture

## 1. Главная архитектурная позиция

Flexity — основная FastAPI multi-tenant ERP-платформа.

Все новые универсальные бизнес-функции разрабатываются во Flexity, а не в отдельных Flask-проектах.

Trailers, детский сад, консалтинг, клиника и другие отрасли должны подключаться к Flexity как:

* industry templates — если достаточно настроек;
* industry packages — если нужна отдельная отраслевая бизнес-логика.

Старые Flask-проекты (Trailers, Consulting, Clinic) — **reference systems**: источник бизнес-логики для обобщения во Flexity, а не целевая архитектура. Код Flask **не копировать напрямую**.

## 2. Роли текущих проектов

### Flexity

Главная целевая платформа.

Содержит:

* tenants;
* auth;
* roles / permissions;
* module registry;
* subscriptions;
* parties;
* workflows / CRM;
* catalog;
* documents;
* finance;
* accounting;
* integrations;
* AI foundation;
* audit;
* future data quality;
* future learning;
* future inventory;
* future production.

### Trailers Flask

Legacy/reference-проект.

Используется как источник:

* бизнес-логики;
* процессов;
* ролей;
* статусов;
* форм;
* маршрутов;
* документов;
* ошибок и реальных сценариев.

Не является целевой платформой.

Целевое состояние: industry_trailers package внутри Flexity.

### Детский сад

Первый подписочный клиент / tenant внутри Flexity.

Не создавать отдельный Flask-проект.

Целевое состояние: kindergarten_basic template + доработки внутри Flexity.

### Консалтинг

Будущий consulting_basic template внутри Flexity.

Если есть старый Flask-проект — использовать его как reference, но новые CRM, документы, оплаты и AI делать во Flexity.

### Clinic App Flask

Legacy/reference-проект.

Используется как источник бизнес-логики для clinic_basic template / future industry_clinic package.

Целевое состояние: clinic_basic template внутри Flexity.

Не поддерживать Clinic Flask как параллельную долгосрочную продуктовую линию.

## 2.1 Четыре reference-направления (validation)

Эти направления **не отдельные CRM**. Они валидируют универсальную модель Flexity через industry templates/packages.

### Kindergarten (kindergarten_basic)

Валидирует:

* recurring services / абонементы;
* documents (договоры, заявления);
* payments / finance;
* packages / subscriptions;
* parties (родитель / ребёнок) через универсальный parties + metadata.

### Consulting (consulting_basic)

Валидирует:

* CRM / leads;
* commercial proposals;
* contracts;
* retainers;
* tasks;
* acts / reports;
* payments.

### Clinic (clinic_basic)

Валидирует:

* leads;
* call-center workflow;
* appointments;
* service execution / visit-like flow;
* payments.

### Trailers (trailers_basic / industry_trailers)

Валидирует:

* CRM-to-order;
* reservation / availability;
* fulfillment / production;
* warehouse / location;
* VIN-like asset and integration references.

## 3. Разделение template и package

### Industry Template

Используется, если отрасль отличается настройками:

* названиями сущностей;
* кастомными полями;
* воронками;
* статусами;
* шаблонами документов;
* прайсами;
* простыми отчетами.

Примеры:

* детский сад;
* консалтинг;
* образовательный центр;
* сервисная компания;
* небольшая клиника.

### Industry Package

Используется, если нужна отдельная бизнес-логика и код.

Примеры:

* Trailers.

Для Trailers нужны:

* VIN;
* ОТТС;
* конфигуратор прицепов;
* BOM / спецификации;
* производственные маршруты;
* склад полуфабрикатов;
* себестоимость прицепа;
* документы на прицеп;
* жизненный цикл изделия.

## 4. Tenant Customization Layer

Flexity поддерживает отдельный слой клиентской кастомизации поверх industry templates и industry packages.

Целевая архитектура слоёв:

    Flexity Core
    -> Universal modules
    -> Industry template / industry package
    -> Tenant customization

### Назначение

Tenant customization хранит клиентскую конфигурацию, которую нельзя жёстко прописывать в Flexity Core, универсальных модулях или отраслевых пакетах.

Industry templates/packages задают переиспользуемые настройки для сегмента рынка.

Tenant customization задаёт переопределения для конкретного клиента.

### Примеры

Tenant customization может включать:

* логотип клиента;
* фирменные цвета;
* юридические реквизиты компании;
* пакет документов;
* кастомный шаблон договора;
* кастомный шаблон счёта;
* кастомный шаблон акта;
* кастомный шаблон заявки;
* дополнительные поля;
* кастомные метки сущностей;
* настройки воронки;
* настройки уведомлений;
* настройки подписания.

### Порядок разрешения

Для конфигурируемых шаблонов Flexity разрешает настройки в следующем порядке:

    tenant customization
    -> industry template/package default
    -> universal module default
    -> platform fallback

Для шаблонов документов:

    tenant custom template
    -> industry template default
    -> universal document default

### Правило продукта

Клиентские настройки нельзя жёстко прописывать в:

* Flexity Core;
* универсальных модулях;
* industry templates;
* industry packages.

Tenant customization — это не отраслевой модуль.

Это клиентский слой поверх отраслевого поведения.

### Текущий статус

Этот слой — предложенный Change Request и roadmap-пункт (CR-2026-06-05-001).

Не реализовывать в коде до отдельного research brief и утверждённого implementation plan.

## 5. Универсальные модули Flexity

Эти модули нельзя дублировать в отраслевых проектах:

* CRM / workflows;
* parties / контрагенты;
* catalog / номенклатура;
* documents / договоры / подпись;
* finance / счета / оплаты / долги;
* accounting / юрлица / налоговые профили;
* sales;
* inventory;
* production;
* tax;
* HR;
* payroll;
* data quality;
* learning / обучение и допуск;
* AI agents;
* audit;
* integrations;
* subscriptions.

Если новая задача относится к этому списку, её нужно делать во Flexity.

## 6. Текущая карта отраслей

### kindergarten_basic

Тип: industry template.

Нужно закрыть:

* родители;
* дети;
* группы;
* абонементы;
* договоры;
* оплаты;
* долги;
* уведомления;
* подписание договора.

Использовать модули:

* tenants;
* parties;
* workflows;
* catalog;
* documents;
* finance;
* integrations.

### consulting_basic

Тип: industry template.

Нужно закрыть:

* лиды;
* клиенты;
* диагностика;
* коммерческое предложение;
* договор;
* проект;
* задачи;
* акт / отчет;
* оплата;
* AI-ассистент консультанта.

Использовать модули:

* parties;
* workflows;
* documents;
* finance;
* AI;
* audit.

### industry_trailers

Тип: industry package.

Нужно закрыть:

* каталог моделей прицепов;
* конфигуратор;
* комплектации;
* VIN;
* ОТТС;
* заказы покупателей;
* резерв со склада;
* заявка в производство;
* BOM;
* производственные маршруты;
* выпуск;
* документы;
* отгрузка;
* себестоимость.

Использовать универсальные модули:

* parties;
* workflows;
* catalog;
* sales;
* inventory;
* production;
* documents;
* finance;
* accounting;
* audit;
* AI.

## 7. Первичный порядок разработки

### Текущий приоритет: W3 Manager Operations

Универсальный менеджерский поток во Flexity tenant workspace:

    client (party)
    -> work item
    -> activity / task
    -> stage transition
    -> document
    -> invoice / payment

**Не начинать** до завершения этого потока (если нет отдельного approval):

* child / group / attendance (детский сад);
* medical records / MedElement (клиника);
* VIN / production / warehouse depth (Trailers);
* consulting-specific project accounting.

### Долгосрочный порядок

1. Стабилизировать Flexity как платформу.
2. Завершить W3 Manager Operations (read + controlled write в universal modules).
3. Развивать kindergarten_basic как первый коммерческий validation tenant/template.
4. Развивать consulting_basic и clinic_basic как validation templates.
5. Параллельно анализировать Trailers Flask как reference.
6. Составить карту миграции Trailers Flask → Flexity industry_trailers.
7. Только после карты начинать кодировать industry_trailers package.

## 8. Главные запреты

Нельзя:

* строить вторую CRM в Trailers;
* строить вторую CRM для детского сада;
* строить вторую CRM для консалтинга;
* строить вторую CRM для клиники;
* поддерживать Clinic / Consulting / Trailers Flask как параллельные долгосрочные продукты;
* копировать legacy Flask-код напрямую во Flexity;
* строить второй механизм подписки;
* строить второй механизм документов;
* строить второй AI-оркестратор;
* переносить Trailers целиком без карты;
* превращать Flexity сразу в микросервисы без необходимости.

На текущем этапе целевая архитектура — модульный монолит на FastAPI.
Микросервисы и событийная архитектура возможны позже, когда появится нагрузка, команда и стабильные границы модулей.
