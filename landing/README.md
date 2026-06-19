# Flexity Landing (www.flexity.asia)

Публичный маркетинговый сайт Flexity — статический контент-воронка в репозитории.

## Live

| URL | Назначение |
|-----|------------|
| https://www.flexity.asia/ | Landing (static) |
| https://flexity.asia/ | 301 → www (корень) |
| https://flexity.asia/console/login | Platform Console login |

Deploy path на сервере: `/var/www/flexity-landing/`

## Структура

```text
landing/
  README.md
  www/
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

## Сообщение сайта

Flexity — **единая** AI-ready CRM/ERP-платформа. Clinic, Consulting, Kindergarten и Trailers — **направления внедрения**, не отдельные продукты.

Универсальный workflow: клиент → заявка/work item → документ → счёт/оплата → исполнение.

## Ссылки входа

| Элемент | URL |
|---------|-----|
| Кнопка «Войти в систему» | `https://flexity.asia/console/login` |

Не использовать как primary CTA: `admin.flexity.asia`, `/auth/login`, прямые ссылки на legacy Flask apps.

## Локальный preview

```bash
cd landing/www
python -m http.server 8080
```

Откройте: http://localhost:8080/

## Проверки перед deploy

```bash
grep -R "admin.flexity\|auth/login\|clinic.flexity" landing/www || true
grep -R "console/login" landing/www
```

## Deploy

Только с approval — см. [deploy/console-and-landing.md](../deploy/console-and-landing.md).

```bash
tar -C landing/www -cf - . | ssh flexity 'rm -rf /var/www/flexity-landing && mkdir -p /var/www/flexity-landing && tar -xf - -C /var/www/flexity-landing'
```

## Статус разделов

| Раздел | Статус |
|--------|--------|
| Решения | Каркас + 4 направления |
| Insights | Индекс рубрик (скоро) |
| Кейсы | Placeholder + формат |
| Калькуляторы | Индекс, страницы «готовится» |
| Демо | Статика, контакты; CRM lead capture — позже |
