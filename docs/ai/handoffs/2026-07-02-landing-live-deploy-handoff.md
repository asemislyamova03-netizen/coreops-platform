# Session Handoff: 2026-07-02

## Branch

`main` @ `f221bf1`

## Goal

Обновить live `www.flexity.asia` до `origin/main` commit `f221bf1` — deploy только `landing/www/`.

## Status

**Done.** Live landing совпадает с git `f221bf1`. Backend/nginx/env/Core не трогались.

## Files changed (this session)

- **Live server only:** `/var/www/flexity-landing/` (37 файлов из `landing/www/`)
- **Git:** без новых commit/push в этой сессии

## Checks run

- `main`, `HEAD = f221bf1` — OK
- Backup: `/var/www/flexity-landing.backup.20260702-192843-f221bf1`
- HTTP 200: `/`, `/services/`, `/diagnostics/free.html`, `/demo/`, `/solutions/`, `/insights/`, `/insights/crm-cash-gap.html`
- `/demo/`: `inboundLeadForm`, consent, honeypot, блок диагностики, navbar CTA — OK
- API `POST /api/v1/public/leads`: `403 Public lead capture is disabled` — форма в HTML есть, intake выключен

## Decisions

- Тестовый лид не создавали: `PUBLIC_LEADS_ENABLED` на production выключен
- Stash не pop'ался
- WIP backend/booking/platform-console не в deploy

## Risks

- Rollback доступен через backup `20260702-192843-f221bf1`
- Форма на `/demo/` видна, но не принимает лиды до Phase 6

## Next safe step

**Phase 6:** включить `PUBLIC_LEADS_ENABLED` и связанные env по `docs/ai/plans/2026-06-24-public-inbound-leads-runbook.md`, перезапустить backend, осторожно протестировать форму.

Альтернатива: следующий content slice — платные форматы в `landing/www/diagnostics/`.

## Do not do next

- Не pop stash без явного запроса
- Не commit/push WIP booking без отдельного approval
- Не менять nginx/env при landing-only работе
- Не говорить, что intake лидов live, пока `PUBLIC_LEADS_ENABLED=true`
