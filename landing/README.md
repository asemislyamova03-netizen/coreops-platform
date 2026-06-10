# Flexity Landing (www.flexity.asia)

Локальная копия публичного лендинга **www.flexity.asia** в репозитории Flexity.

## Источник

| Поле | Значение |
|------|----------|
| Live URL | https://www.flexity.asia/ |
| Дата копии | 2026-06-10 |
| Способ | `curl -sL https://www.flexity.asia/` + скачивание `flexity-logo.svg` и `favicon.ico` |
| Live deploy | **не выполнялся** в рамках Stage B |

Структура:

```text
landing/
  README.md
  www/
    index.html
    assets/
      flexity-logo.svg
      favicon.ico
```

## Локальный preview

```bash
cd landing/www
python -m http.server 8080
```

Откройте: http://localhost:8080/

Bootstrap и Yandex.Metrika загружаются с внешних CDN (нужен интернет).

## Ссылки входа

| Элемент | URL |
|---------|-----|
| Кнопка «Войти в систему» (navbar) | https://flexity.asia/console/login |

Legacy login (`admin.flexity.asia`, `flexity.asia/auth/login`) убраны из этой копии.

Карточка «Консалтинг» ведёт на `#contacts` («Запросить доступ»), не на legacy Consult login.

## Пути, работающие только на production www

Следующие ссылки остаются как на live-сайте и **не работают** при локальном preview без отдельной выкладки:

- `/demo/`
- `/calculators/our-vs-snr.html`
- `/calculators/trucking-trips.html`

## Целевой deploy path (сервер)

```text
/var/www/flexity-landing/
```

Инструкция nginx: [deploy/console-and-landing.md](../deploy/console-and-landing.md).

Deploy на сервер (rsync, nginx reload) — только с отдельным approval. В Stage B не выполнялся.

## Обновление копии

```bash
curl -sL "https://www.flexity.asia/" -o landing/www/index.html
curl -sL "https://www.flexity.asia/flexity-logo.svg" -o landing/www/assets/flexity-logo.svg
curl -sL "https://www.flexity.asia/favicon.ico" -o landing/www/assets/favicon.ico
```

После обновления проверить:

- кнопка «Войти в систему» → `https://flexity.asia/console/login`
- нет `admin.flexity.asia/auth/login` и `flexity.asia/auth/login`
