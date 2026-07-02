# Implementation Plan: Landing funnel content slice (services + free diagnostics + homepage CTA)

**Дата:** 2026-07-02  
**Ветка (целевая):** `Сайт Flexity — структура и тексты`  
**Статус:** waiting for approval  
**Основание:** [docs/FLEXITY_WEBSITE_AUDIT_AND_STRUCTURE.md](../../FLEXITY_WEBSITE_AUDIT_AND_STRUCTURE.md)  
**Master plan:** [2026-06-19-site-marketing-content-plan.md](2026-06-19-site-marketing-content-plan.md) — Phase 1 (public site funnel, static only)

---

## Goal

Сделать **минимальный контентный слайс** публичного сайта Flexity: превратить главную и два новых раздела в понятную входную точку воронки **без deploy, без смены дизайна, без backend**.

После слайса посетитель должен:
1. Понять, **какие услуги** оказывает Flexity (не только «что за платформа»).
2. Увидеть **бесплатную диагностику** как главный низкопороговый вход.
3. С главной попасть на диагностику или услуги одним кликом.

**Не в scope этого слайса:** форма лидов, API, платные страницы диагностики, модули, обновление navbar на всех 13 страницах, deploy.

---

## Classification

| Поле | Значение |
|------|----------|
| **Project** | Flexity |
| **Category** | `documentation_only` → static landing content (Phase 1 funnel) |
| **Risk level** | low |
| **Backend** | forbidden |
| **Deploy / nginx** | forbidden |
| **Design system** | forbidden (только существующие классы Bootstrap + `site.css`) |

### Coordinator block

1. **Project:** Flexity  
2. **Category:** documentation_only / static landing (Phase 1)  
3. **Risk level:** low  
4. **Intended scope:** `landing/www/diagnostics/free.html`, `landing/www/services/index.html`, `landing/www/index.html`, `landing/README.md` (status note)  
5. **Forbidden scope:** `backend/`, `platform-console/`, `deploy/`, nginx, `.env`, остальные HTML-страницы landing (кроме перечисленных), `assets/site.css` (без необходимости)  
6. **Required plan:** этот документ → approval → код → локальная проверка (без deploy)

---

## Scope

### Deliverables

| # | URL (локально) | Файл | Действие |
|---|----------------|------|----------|
| 1 | `/diagnostics/free.html` | `landing/www/diagnostics/free.html` | **Создать** |
| 2 | `/services/` | `landing/www/services/index.html` | **Создать** |
| 3 | `/` | `landing/www/index.html` | **Правка текста и CTA** (hero + один блок) |
| 4 | — | `landing/README.md` | **Мини-обновление** route map + статус слайса |

### Files to modify

```
landing/www/diagnostics/free.html   (new)
landing/www/services/index.html     (new)
landing/www/index.html              (edit)
landing/README.md                   (edit, routes only)
```

### Files not to touch

```
backend/**
platform-console/**
deploy/**
landing/www/assets/site.css         (unless broken link found)
landing/www/demo/index.html         (follow-up: ссылка на free diagnostics)
landing/www/solutions/**
landing/www/insights/**
landing/www/cases/**
landing/www/calculators/**
scripts/**
docs/FLEXITY_WEBSITE_AUDIT_AND_STRUCTURE.md  (frozen audit)
```

### Навигация — осознанное ограничение

В этом слайсе **не обновляем navbar на всех 13 страницах** — это отдельный follow-up PR.

На **новых страницах** и **главной** добавляем пункты:
- «Услуги» → `/services/`
- «Диагностика» → `/diagnostics/free.html`

На остальных страницах navbar остаётся прежним до следующего слайса.

---

## Content specification

### 1. `landing/www/diagnostics/free.html`

**Шаблон:** копировать структуру `landing/www/demo/index.html` (navbar, `page-hero`, `contact-card`, `workflow-steps`, footer). Без новых CSS-классов.

**Meta:**
- `<title>`: `Бесплатная диагностика процесса — Flexity`
- `<meta name="description">`: кратко — 30–45 мин, карта процесса, следующий шаг без обязательств

**Контент:**

| Блок | Текст (смысл) |
|------|----------------|
| Badge | `Бесплатный вход` |
| H1 | `Бесплатная диагностика процесса` |
| Lead | Для владельца или руководителя операций, если «что-то разъехалось» между Excel, мессенджерами и учётом — но ещё рано говорить о большом проекте. |
| Для кого | Владельцы и операционные директора сервисного и операционного бизнеса. |
| Что проверяем | 1–2 ключевых процесса: заявки, документы, оплаты, где теряется информация. |
| Формат | 30–45 минут созвон или структурированная переписка. |
| Что получаете | Карта «как сейчас», 3–5 наблюдений, рекомендация следующего шага. **Не КП и не внедрение** — ясность. |
| Что будет дальше (ol) | 1) Созвон/переписка → 2) Краткий разбор → 3) Рекомендация: платная диагностика, демо платформы или пауза |
| CTA primary | `Записаться на диагностику` → `/demo/` (с якорем или query `?intent=free-diagnostic` — опционально, текст в WhatsApp) |
| CTA secondary | `Посмотреть услуги` → `/services/` |
| Контакты | Те же: email, WhatsApp, Telegram — с подсказкой «укажите, что интересует бесплатная диагностика» |
| Честная оговорка | Форма на сайте в разработке; заявка через мессенджер или email. |

**Navbar на странице:** Решения · **Услуги** · **Диагностика** (active) · Insights · Кейсы · Калькуляторы · Демо

---

### 2. `landing/www/services/index.html`

**Шаблон:** `landing/www/solutions/index.html` — сетка `card-module`, без нового дизайна.

**Meta:**
- `<title>`: `Услуги — Flexity`
- `<meta name="description">`: аудит, автоматизация, модули, сопровождение — партнёр по внедрению, не только SaaS

**Контент:**

| Блок | Текст (смысл) |
|------|----------------|
| Badge | `Как мы работаем с клиентом` |
| H1 | `Услуги Flexity` |
| Lead | Flexity — платформа и команда внедрения: сначала разбираем процесс, потом подключаем модули по этапам. |
| Карточки услуг (8 шт., без отдельных URL в этом слайсе) | см. таблицу ниже |
| Блок «С чего начать» | Бесплатная диагностика → платная диагностика / демо → проект |
| CTA primary | `Бесплатная диагностика` → `/diagnostics/free.html` |
| CTA secondary | `Запросить демо` → `/demo/` |

**Карточки услуг (краткий текст в каждой card-module):**

| Услуга | Проблема (1 строка) | Результат (1 строка) |
|--------|---------------------|----------------------|
| Аудит процессов | Непонятно, где теряются деньги и заявки | Карта процесса и приоритеты |
| Автоматизация бизнеса | Ручная рутина и дублирование данных | Связный контур CRM + документы + финансы |
| CRM / tenant-система | Хаос в заявках и клиентах | Единая воронка на Flexity Core |
| Разработка модулей | Отраслевой сценарий не закрыт шаблоном | Подключение industry package |
| AI-сотрудники | Рутина съедает время команды | Сценарии автоматизации (без «магии из коробки») |
| ContentOps | Контент не связан с продажами | Система публикаций и контент-контур |
| Интеграции | Данные в разных системах | Поэтапная связка с внешними сервисами |
| Сопровождение | После запуска процесс снова разъезжается | Развитие и поддержка tenant |

**Navbar:** Решения · **Услуги** (active) · **Диагностика** · Insights · …

---

### 3. `landing/www/index.html` — правки

**Только текст и ссылки.** Layout, классы, цвета — без изменений.

#### 3.1 Hero — подзаголовок (добавить клиентский слой)

**Было:** только про направления внедрения и workflow.

**Станет:** после текущего абзаца или заменой второй части — добавить 1–2 предложения:

> Если заявки, документы и оплаты живут в разных местах — мы сначала проводим диагностику процесса, затем внедряем Flexity по этапам.

(Точная формулировка при реализации — не длиннее 2 предложений.)

#### 3.2 Hero — CTA

| Кнопка | Было | Станет | href |
|--------|------|--------|------|
| Primary | Запросить демо | **Бесплатная диагностика** | `/diagnostics/free.html` |
| Secondary | Посмотреть решения | **Услуги** (или «Посмотреть услуги») | `/services/` |

Третья ссылка мелким текстом под кнопками (optional):
- «Запросить демо платформы» → `/demo/`

#### 3.3 Navbar (только на главной)

Добавить после «Решения»:
- `Услуги` → `/services/`
- `Диагностика` → `/diagnostics/free.html`

#### 3.4 Секция `#how` — шаг 1

**Было:** «Выбираете направление и оставляете заявку» → Демо.

**Станет:** «Начинаете с бесплатной диагностики или заявки» → ссылка на `/diagnostics/free.html` и `/demo/`.

---

### 4. `landing/README.md`

Обновить:
- Route structure: добавить `/diagnostics/free.html`, `/services/`
- Статус: отметить content slice 2026-07-02 (local, not deployed)
- Исправить строку Insights «статей нет» → «3 статьи» (если ещё не исправлено)

---

## Steps

| Step | Действие | Проверка |
|------|----------|----------|
| 1 | Создать `landing/www/diagnostics/` и `free.html` по шаблону demo | Файл открывается локально |
| 2 | Создать `landing/www/services/index.html` по шаблону solutions | Файл открывается локально |
| 3 | Править `landing/www/index.html` (hero, CTA, nav, #how) | Diff только текст/ссылки |
| 4 | Обновить `landing/README.md` routes | Markdown diff |
| 5 | Локальный preview | `cd landing/www && python -m http.server 8080` |
| 6 | Grep-проверки | см. Tests |

**Не делать:** deploy, commit (без запроса), backend, правки `site.css`.

---

## Tests / checks

### Локальный preview

```bash
cd landing/www
python -m http.server 8080
```

Открыть:
- http://localhost:8080/
- http://localhost:8080/diagnostics/free.html
- http://localhost:8080/services/

### Grep (safe)

```bash
# Нет запрещённых ссылок
grep -R "admin.flexity\|auth/login" landing/www/diagnostics landing/www/services landing/www/index.html || true

# Новые маршруты существуют
test -f landing/www/diagnostics/free.html && test -f landing/www/services/index.html

# Console login на главной сохранён
grep "console/login" landing/www/index.html

# Нет обещания live CRM form
grep -i "форма.*работает\|lead capture.*live" landing/www/diagnostics/free.html landing/www/services/index.html || true
```

### Ручной чеклист

- [ ] Hero: primary CTA ведёт на бесплатную диагностику
- [ ] Тексты клиентские, без новых технических терминов в hero
- [ ] Страницы используют те же Bootstrap + `site.css`, без inline redesign
- [ ] Контакты и честные оговорки про форму сохранены
- [ ] Breadcrumbs работают на новых страницах
- [ ] Mobile: navbar collapse не сломан

---

## Risks

| Риск | Митигация |
|------|-----------|
| Navbar разный на главной и остальных страницах | Зафиксировано как follow-up; не расширять scope |
| `/services/` vs `/services/index.html` | Использовать ссылки `/services/` как на solutions |
| Клиент ожидает онлайн-форму на free diagnostic | Явная оговорка + мессенджеры |
| Дублирование с `/demo/` | Развести смысл: диагностика = вход, демо = показ платформы |
| Deploy до approval | Не деплоить; только local |

---

## Rollback

```bash
git checkout -- landing/www/index.html landing/README.md
git clean -fd landing/www/diagnostics landing/www/services
```

Или удалить вручную:
- `landing/www/diagnostics/free.html`
- `landing/www/services/index.html`
- откатить diff в `index.html` и `README.md`

---

## Follow-up (не этот слайс)

1. Navbar sync на всех страницах landing  
2. `/diagnostics/index.html` — обзор платных форматов  
3. `/demo/` — ссылка «пришли с бесплатной диагностики»  
4. Phase 6: форма + `POST /api/v1/public/leads`  
5. CTA block в шаблоне Insights  
6. Deploy `landing/www/` → production (отдельный approve)

---

## Approval

| | |
|---|---|
| **Status** | approved — implemented 2026-07-02 (local only, no deploy) |
| **Approved by** | user |
| **Date** | 2026-07-02 |

После approval: реализовать шаги 1–5, показать diff, **не деплоить** без отдельного решения.

---

## HQ Summary

1. **Что делаем:** 2 новые static-страницы + правка CTA/текста на главной.  
2. **Чего не делаем:** deploy, backend, дизайн, остальные 11 HTML-страниц.  
3. **Главный результат:** бесплатная диагностика и услуги становятся кликабельными входами воронки.  
4. **Следующий шаг после кода:** локальный preview → approval deploy (отдельно) или navbar sync slice.
