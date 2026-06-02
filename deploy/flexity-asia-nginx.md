# CoreOps на flexity.asia (текущий режим)

**Сейчас на сервере остаются:** Consult (`/`, порт 8002), Trailers (`/trailers/`, 8003), лендинг www, clinic и пр.  
**CoreOps добавляем рядом**, ничего из этого не трогаем.

Позже (отдельным этапом): перенос Trailers/Consult к клиентам, очистка сервера, перенос на **flexity.kz**.

---

## Текущая схема (сосуществование)

| URL | Сервис | Порт |
|-----|--------|------|
| `flexity.asia/` | Consult | 8002 |
| `flexity.asia/trailers/` | Trailers | 8003 |
| `flexity.asia/demo/` | Статика | — |
| **`flexity.asia/api/`** | **CoreOps** | **8005** |
| **`flexity.asia/docs`** | **CoreOps Swagger** | **8005** |

```text
Код:     /opt/flexity/coreops
venv:    /opt/flexity/envs/coreops
Сервис:  coreops.service → uvicorn 127.0.0.1:8005
БД:      PostgreSQL, database coreops (отдельно от consult/clinic)
```

Порт **8005** — чтобы не пересечься с 8002 (Consult) и 8003 (Trailers).

---

## Nginx: что добавить в flexity.asia.conf

Блоки **выше** `location /` (который proxy на 8002):

```nginx
    # --- CoreOps Platform (staging) ---
    location ^~ /api/ {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location = /docs {
        proxy_pass http://127.0.0.1:8005/docs;
        proxy_set_header Host              $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /openapi.json {
        proxy_pass http://127.0.0.1:8005/openapi.json;
        proxy_set_header Host              $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
```

Не менять: `/trailers/`, `/demo/`, `location /` → 8002.

Проверка:

```bash
curl -s https://flexity.asia/api/v1/health
curl -sI https://flexity.asia/          # Consult как раньше
curl -sI https://flexity.asia/trailers/ # Trailers как раньше
```

---

## Деплой (кратко)

```bash
# на сервере
sudo mkdir -p /opt/flexity/coreops && sudo chown ubuntu:ubuntu /opt/flexity/coreops
cd /opt/flexity/coreops && git clone <REPO_URL> .

python3 -m venv /opt/flexity/envs/coreops
/opt/flexity/envs/coreops/bin/pip install -e backend
cd backend && cp .env.example .env   # DATABASE_URL, SECRET_KEY, SEED_ON_STARTUP=true
# создать БД coreops в Postgres
/opt/flexity/envs/coreops/bin/alembic upgrade head

# systemd coreops.service → uvicorn --host 127.0.0.1 --port 8005
sudo systemctl enable --now coreops
sudo nginx -t && sudo systemctl reload nginx
```

Подробнее: [server-setup.md](server-setup.md).

---

## Позже: после ухода Consult/Trailers и переезд на .kz

1. **Lightsail:** освободить 8002, перенести CoreOps на 8002, корень — статика (см. историю в git / старые версии этого файла).
2. **flexity.kz:** тот же layout `/api/` + `/docs`, дамп БД `coreops`.

До тех пор staging = **flexity.asia** только с префиксом `/api/`.
