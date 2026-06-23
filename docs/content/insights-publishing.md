# Insights Publishing

Flexity publishes public insights as static HTML under `landing/www/insights/`.

Channel overview (Telegram, Instagram, Insights operational; TikTok planned): [Content Factory](content-factory.md).

The source format is markdown with frontmatter:

```text
landing/content/articles/YYYY-MM-DD-slug.md
```

Required frontmatter:

```yaml
title: "..."
date: "YYYY-MM-DD"
category: "..."
slug: "..."
status: "draft"
description: "..."
source: "..."
cta: "..."
image: "/assets/social/YYYY-MM-DD-slug/instagram-feed.png"
```

Only articles with `status: approved` or `status: published` are generated into the public site. Draft articles are ignored.

## Generate

```powershell
python scripts/content/generate_insights.py
```

The generator writes:

```text
landing/www/insights/index.html
landing/www/insights/{slug}.html
```

It validates required frontmatter, unique public slugs, article dates, status values, and image path format.

## Safety

- No backend is used.
- No CMS is used.
- No deploy is performed by the generator.
- Telegram and Instagram publishers do not read article markdown.
- Public content must not claim unfinished Flexity features as ready.
- Use honest wording such as "развиваем", "закладываем", and "можно настроить" when describing roadmap-adjacent capabilities.

## Checks

```powershell
python -m unittest discover -s tests/scripts/content -p "test_generate_insights.py" -v
python -m compileall scripts/content/generate_insights.py tests/scripts/content/test_generate_insights.py
git diff --check
git status --short
```
