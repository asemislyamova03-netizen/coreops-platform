# Flexity Landing (www.flexity.asia)

Публичный маркетинговый сайт Flexity — статический контент-воронка в репозитории.

**Master plan (marketing / content / i18n):** [docs/ai/plans/2026-06-19-site-marketing-content-plan.md](../docs/ai/plans/2026-06-19-site-marketing-content-plan.md)
**Change Request:** [CR-2026-06-19-001](../docs/ai/CHANGE_REQUESTS.md#cr-2026-06-19-001-public-site-content-funnel-multilingual-and-marketing-operations)

---

## Live

| URL | Назначение |
|-----|------------|
| https://www.flexity.asia/ | Landing (static, RU root) |
| https://flexity.asia/ | 301 → www (корень) |
| https://flexity.asia/console/login | Platform Console login (branded, RU-first UI) |

| Deploy path (server) | Содержимое |
|----------------------|------------|
| `/var/www/flexity-landing/` | `landing/www/` — публичный сайт |
| `/opt/flexity/coreops/platform-console/dist/` | Platform Console SPA (**не** часть landing) |

---

## Route structure

```text
/                          → homepage (RU)
/solutions/                → index направлений
/solutions/clinic.html
/solutions/consulting.html
/solutions/kindergarten.html
/solutions/trailers.html
/insights/                 → индекс рубрик (каркас)
/cases/                    → placeholder кейсов
/calculators/              → индекс калькуляторов
/demo/                     → демо и контакты (статика)
```

**Не в scope landing repo:** `/console/*` (Platform Console), `/api/v1/*` (Flexity backend).

---

## Структура репозитория

```text
landing/
  README.md          ← этот файл (status + boundaries)
  www/               ← deploy source (static HTML/CSS)
    index.html
    assets/
      flexity-logo.svg
      favicon.ico
      site.css
    solutions/
      index.html
      clinic.html
      consulting.html
      kindergarten.html
      trailers.html
    insights/
      index.html
    cases/
      index.html
    calculators/
      index.html
    demo/
      index.html
```

---

## Сообщение сайта

Flexity — **единая** AI-ready CRM/ERP-платформа. Clinic, Consulting, Kindergarten и Trailers — **направления внедрения**, не отдельные продукты.

Универсальный workflow: клиент → заявка/work item → документ → счёт/оплата → исполнение.

Публичный контент **не должен** обещать как готовое то, что ещё в roadmap (CRM lead form, multilingual, content agent, S2.2/S2.3/W3.2+).

---

## Ссылки входа

| Элемент | URL |
|---------|-----|
| Кнопка «Войти в систему» | `https://flexity.asia/console/login` |

Не использовать как primary CTA: `admin.flexity.asia`, `/auth/login`, прямые ссылки на legacy Flask apps.

---

## Текущий статус (2026-06-19)

| Область | Статус |
|---------|--------|
| Homepage | ✅ Live |
| Solutions (4 направления) | ✅ Каркас + контент |
| Insights | 🟡 Индекс рубрик, статей нет |
| Cases | 🟡 Placeholder + формат |
| Calculators | 🟡 Индекс, страницы «готовится» |
| Demo / contacts | ✅ Статика |
| CTA → Console login | ✅ |
| Yandex.Metrika | 🟡 Частично |
| SEO (sitemap, robots, meta matrix) | ❌ Не сделано |
| RSS | ❌ |
| Multilingual `/en/`, `/kk/` | ❌ Запланировано (Phase 2) |
| CRM lead form | ❌ Phase 6, отдельный backend approve |
| Content agent | ❌ Phase 4, drafts only |
| Social auto-publish | ❌ |

**Platform Console (отдельный deploy):** W3.1 manager workspace, branded login, Russian UI polish (S2.1b) — live на `flexity.asia/console/`.

---

## Roadmap boundaries

Работа по сайту разбита на фазы — **не смешивать** в одной ветке с console/backend:

| Phase | Scope | Touch `landing/www/`? |
|-------|--------|------------------------|
| 0 | Close current PR | — |
| 1 | Public site funnel, honest CTA | ✅ static only |
| 2 | Multilingual architecture (plan) | docs first |
| 3 | Insights/cases templates + content | ✅ static |
| 4 | Content agent drafts | docs / `docs/content/` only |
| 5 | Target/social, UTM, Metrika goals | landing + docs |
| 6 | CRM lead capture | backend + landing (отдельный approve) |
| 7 | Product S2.2/S2.3/W3.2+ | `platform-console/`, `backend/` |

**Этот README и master plan** — границы и статус. Изменения HTML — только в рамках approved plan на фазу.

---

## Локальный preview

```bash
cd landing/www
python -m http.server 8080
```

Откройте: http://localhost:8080/

---

## Проверки перед deploy

```bash
grep -R "admin.flexity\|auth/login\|clinic.flexity" landing/www || true
grep -R "console/login" landing/www
```

---

## Deploy

Только с approval — см. [deploy/console-and-landing.md](../deploy/console-and-landing.md).

```bash
tar -C landing/www -cf - . | ssh flexity 'rm -rf /var/www/flexity-landing && mkdir -p /var/www/flexity-landing && tar -xf - -C /var/www/flexity-landing'
```

**Deploy boundary:** эта команда обновляет **только** `/var/www/flexity-landing/`. Console deploy — отдельная команда в `platform-console/dist/`.

---

## Out of scope (landing README / plan level)

- `backend/**`
- `platform-console/**` (кроме ссылок login)
- nginx/systemd changes
- legacy Flask apps
- content agent implementation
- full i18n implementation
- social API credentials
- `.env` / secrets
