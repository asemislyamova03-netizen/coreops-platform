# Flexity Content Bank

## 1. Назначение документа

Этот документ фиксирует approved content bank Flexity по итогам мозгового штурма от 28 июня 2026.

Документ является рабочим источником тем, рубрик и ограничений для Маргоси и будущего ContentOps selector/preflight слоя. Он нужен, чтобы daily content не уходил в одну повторяющуюся тему и не строился из случайной генерации.

## 2. Source of Truth

Маргося не придумывает контент-план с нуля, а выбирает темы только из approved content bank.

Для каждого draft pack должна быть явная ссылка на тему банка:

```yaml
content_bank:
  topic_id: "<approved-topic-id>"
```

Если `docs/content/flexity-content-bank.md` отсутствует, не читается или не содержит подходящей approved темы, генерация daily content должна fail-closed.

## 3. Workflow

```text
content bank
-> рубрика дня
-> duplicate check
-> draft pack
-> approval
-> publish
-> publish_log
```

Публикация не разрешается этим документом. Любой publish по-прежнему требует отдельного approval и должен записываться в `publish_log.yml`.

## 4. Рубрики

- Авторская колонка Асем
- Идеи для вайбкодинга и AI-проектов
- Новости недели и выводы
- Build in public
- Работа с аудиторией
- Креативное применение AI
- Личная жизнь / сторизы
- Практические бизнес-сценарии
- Продуктовое видение Flexity

## 5. Темы Банка

### CB-2026-06-28-001

```yaml
id: CB-2026-06-28-001
rubric: Личная жизнь / сторизы
title: Меню по холодильнику / планирование покупок продуктов с помощью ИИ
angle: Как AI может снизить бытовую ментальную нагрузку: посмотреть, что есть дома, предложить меню, собрать список покупок и встроить это в планы недели.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-002

```yaml
id: CB-2026-06-28-002
rubric: Практические бизнес-сценарии
title: Договоры / кассовый разрыв / CRM
angle: Почему договоры, оплаты, долги и CRM должны быть связаны в одном процессе, иначе собственник видит кассовый разрыв слишком поздно.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-003

```yaml
id: CB-2026-06-28-003
rubric: Практические бизнес-сценарии
title: Bitrix
angle: Где Bitrix помогает бизнесу, где начинает упираться в процессы, и почему важно сначала описать управленческую логику, а потом выбирать инструмент.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-004

```yaml
id: CB-2026-06-28-004
rubric: Практические бизнес-сценарии
title: Данные и бизнес-процессы
angle: Данные становятся полезными только тогда, когда понятно, какой процесс они объясняют и какое решение помогают принять.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-005

```yaml
id: CB-2026-06-28-005
rubric: Продуктовое видение Flexity
title: 1С / ERP нового поколения
angle: Как может выглядеть ERP нового поколения: не только учет и справочники, а операционная система с AI-помощниками, процессами и управленческими подсказками.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-006

```yaml
id: CB-2026-06-28-006
rubric: Креативное применение AI
title: Делегирование AI
angle: Что можно делегировать AI уже сейчас, где нужен контроль человека, и как не превратить AI в еще один источник хаоса.
channels:
  - telegram
  - instagram
  - reels_tiktok
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-007

```yaml
id: CB-2026-06-28-007
rubric: Креативное применение AI
title: Выкройки / 3D
angle: Как AI и 3D-подходы могут менять проектирование выкроек: от ручной логики к быстрым прототипам, примеркам и персонализации.
channels:
  - telegram
  - instagram
  - reels_tiktok
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-008

```yaml
id: CB-2026-06-28-008
rubric: Креативное применение AI
title: Антропометрия
angle: Почему точные параметры человека важны для персонализированных продуктов, одежды, здоровья и будущих AI-сервисов.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-009

```yaml
id: CB-2026-06-28-009
rubric: Креативное применение AI
title: Профориентация детей
angle: Как AI может помогать детям пробовать роли, проекты и профессии через практические задания, а не только тесты и абстрактные советы.
channels:
  - telegram
  - instagram
  - reels_tiktok
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-010

```yaml
id: CB-2026-06-28-010
rubric: Авторская колонка Асем
title: Босс AI-сотрудников
angle: Новая роль собственника: не делать все самому, а ставить задачи AI-сотрудникам, проверять результат и выстраивать систему контроля.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-011

```yaml
id: CB-2026-06-28-011
rubric: Работа с аудиторией
title: Язык программист vs бизнес
angle: Почему бизнес и разработчики часто говорят о разных вещах, даже когда обсуждают одну задачу, и как переводить идею в понятные требования.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-012

```yaml
id: CB-2026-06-28-012
rubric: Работа с аудиторией
title: Стоимость разработки
angle: Из чего складывается стоимость разработки: не только код, но и понимание процесса, сценарии, ошибки, поддержка и будущие изменения.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-013

```yaml
id: CB-2026-06-28-013
rubric: Идеи для вайбкодинга и AI-проектов
title: AI vs код
angle: Когда AI помогает быстрее собрать прототип, а когда все равно нужны архитектура, проверка, тесты и инженерная ответственность.
channels:
  - telegram
  - instagram
  - reels_tiktok
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-014

```yaml
id: CB-2026-06-28-014
rubric: Идеи для вайбкодинга и AI-проектов
title: Вайбкодинг и личная продуктивность
angle: Как использовать вайбкодинг для личных инструментов: быстрые прототипы, автоматизация рутины, дневники, планы, таблицы и маленькие помощники.
channels:
  - telegram
  - instagram
  - reels_tiktok
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-06-28-015

```yaml
id: CB-2026-06-28-015
rubric: Новости недели и выводы
title: AI в госсекторе
angle: Что новости про AI в госсекторе говорят бизнесу: автоматизация становится инфраструктурной темой, но требования к надежности и ответственности растут.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-06-28
used_at: null
```

### CB-2026-07-01-001

```yaml
id: CB-2026-07-01-001
rubric: Build in public
title: Как мы собираем ContentOps-контур Flexity: от идеи до публикации
angle: Показать процесс сборки ContentOps как продуктовую систему: контент-банк, рубрика дня, проверка дублей, draft pack, approval и только потом публикация.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-07-01
used_at: null
```

### CB-2026-07-01-002

```yaml
id: CB-2026-07-01-002
rubric: Build in public
title: Почему Маргося не должна придумывать темы сама
angle: Объяснить, почему AI-ассистенту нужен утвержденный source of truth: без контент-банка темы повторяются, уходят в одну сторону и теряют связь с реальным планом.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-07-01
used_at: null
```

### CB-2026-07-01-003

```yaml
id: CB-2026-07-01-003
rubric: Build in public
title: Как строится media library для публикаций Flexity
angle: Показать, зачем ContentOps нужна media library: approved assets, стабильные ссылки, права использования, provenance и fail-closed вместо случайных файлов.
channels:
  - telegram
  - instagram
  - insights
status: approved
source_date: 2026-07-01
used_at: null
```

## 6. Правила Выбора Тем

- Не повторять одну рубрику несколько дней подряд без явного calendar override.
- Не брать тему, если она уже опубликована.
- Перед созданием draft pack проверять `publish_log.yml` во всех существующих `landing/content/content-packs/**`.
- Перед созданием draft pack проверять существующие `pack.yml`, `instagram.yml`, `telegram.md`, `instagram.md` и article markdown на совпадение темы, slug и `content_bank.topic_id`.
- Если content bank отсутствует, не читается или не содержит подходящей approved темы, процесс должен fail-closed.
- Запрещена генерация "с нуля" без `content_bank.topic_id`.
- Если calendar задает рубрику дня, selector должен выбирать только approved темы этой рубрики, кроме случая явного override.
- Если backlog topic уже был использован в draft pack, повторное использование требует отдельного approval.

## 7. Next Implementation Step

Следующим шагом нужен отдельный selector/preflight слой для Маргоси.

Минимальный будущий scope:

- читать `docs/content/flexity-content-bank.md`;
- определить рубрику дня из content calendar;
- выбрать одну approved тему;
- проверить дубли по `publish_log.yml`, existing content-packs и article markdown;
- создать только draft pack с `content_bank.topic_id`;
- fail-closed при отсутствии банка, рубрики, approved темы или при риске дубля.

Этот документ не реализует selector/preflight слой, не меняет publisher scripts, не создает content packs, не публикует контент и не разрешает deploy.
