# Flexity / CoreOps Platform

Модульное multi-tenant SaaS-ядро для подписочных бизнес-систем (детский сад, салоны, консалтинг и др. через industry templates).

## Структура репозитория

```
Flexity/
  backend/          # FastAPI API (фазы 0–11)
  README.md         # этот файл
```

## Быстрый старт

```bash
cd backend
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000  
- Swagger: http://localhost:8000/docs  
- Health: http://localhost:8000/api/v1/health  

При старте контейнера выполняются миграции Alembic (`alembic upgrade head`).

## Тесты

```bash
cd backend
pip install -e ".[dev]"
pytest
```

Сценарий MVP из ТЗ (Definition of Done): `tests/test_mvp_scenario.py`

Ручной smoke без pytest:

```bash
cd backend
python scripts/mvp_smoke.py
```

## Документация API

Подробности по модулям и curl-примерам — [backend/README.md](backend/README.md).

## Реализованные фазы backend

| Phase | Модуль |
|-------|--------|
| 0–1 | Bootstrap, Auth, Tenant, Provider |
| 2 | Module registry, Plans, Entitlements |
| 3 | Industry templates |
| 4 | Parties + custom fields |
| 5 | CRM / Workflows |
| 6 | Catalog |
| 7 | Documents |
| 8 | Finance + Accounting |
| 9 | Integrations (mock Bitrix) |
| 10 | AI Foundation |
| 11 | Audit |

## Деплой на сервер

- Staging на **flexity.asia** (рядом с Consult/Trailers): [deploy/flexity-asia-nginx.md](deploy/flexity-asia-nginx.md) — `/api/` → порт **8005**; prod позже на **flexity.kz**
- Общая инструкция: [deploy/server-setup.md](deploy/server-setup.md)
- Готовый `systemd` unit: `deploy/coreops.service`
- Быстрое обновление на сервере: `./deploy/update.sh`
- Docker (опционально): `backend/docker-compose.prod.yml`

## Что не входит в MVP (см. ТЗ)

Полноценный frontend, реальный Bitrix24, банки, ЭП, бухгалтерия с налогами, фоновые воркеры (Celery) — архитектура заложена, реализация позже.
