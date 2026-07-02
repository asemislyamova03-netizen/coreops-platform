from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
ARTICLES_DIR = ROOT / "landing" / "content" / "articles"
INSIGHTS_DIR = ROOT / "landing" / "www" / "insights"
SITE_ORIGIN = "https://www.flexity.asia"
PUBLIC_STATUSES = {"approved", "published"}
REQUIRED_FIELDS = (
    "title",
    "date",
    "category",
    "slug",
    "status",
    "description",
    "source",
    "cta",
    "image",
)
BOOTSTRAP_CSS = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
BOOTSTRAP_CSS_INTEGRITY = (
    "sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
)
BOOTSTRAP_JS = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
BOOTSTRAP_JS_INTEGRITY = (
    "sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz"
)


class InsightsGenerationError(ValueError):
    pass


@dataclass(frozen=True)
class Article:
    path: Path
    title: str
    date: str
    category: str
    slug: str
    status: str
    description: str
    source: str
    cta: str
    image: str
    body: str

    @property
    def url_path(self) -> str:
        return f"/insights/{self.slug}.html"

    @property
    def canonical_url(self) -> str:
        return f"{SITE_ORIGIN}{self.url_path}"

    @property
    def image_url(self) -> str:
        if self.image.startswith("https://"):
            return self.image
        if self.image.startswith("/"):
            return f"{SITE_ORIGIN}{self.image}"
        return f"{SITE_ORIGIN}/{self.image}"


def slug_is_valid(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value))


def parse_frontmatter_value(raw: str) -> str | None:
    value = raw.strip()
    if value == "":
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1]
    return value


def parse_article_file(path: Path) -> Article:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise InsightsGenerationError(f"{path}: missing YAML frontmatter block")
    try:
        _, frontmatter_text, body = text.split("---\n", 2)
    except ValueError as exc:
        raise InsightsGenerationError(
            f"{path}: frontmatter must start and end with ---"
        ) from exc

    frontmatter: dict[str, str | None] = {}
    for line_number, line in enumerate(frontmatter_text.splitlines(), start=2):
        if not line.strip():
            continue
        if ":" not in line:
            raise InsightsGenerationError(
                f"{path}:{line_number}: frontmatter lines must use key: value"
            )
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if key in frontmatter:
            raise InsightsGenerationError(f"{path}: duplicate frontmatter field {key}")
        frontmatter[key] = parse_frontmatter_value(raw_value)

    missing = [
        field
        for field in REQUIRED_FIELDS
        if field not in frontmatter or frontmatter[field] is None
    ]
    if missing:
        raise InsightsGenerationError(
            f"{path}: missing required frontmatter fields: {', '.join(missing)}"
        )

    data = {field: str(frontmatter[field]).strip() for field in REQUIRED_FIELDS}
    if not slug_is_valid(data["slug"]):
        raise InsightsGenerationError(f"{path}: slug must be lowercase kebab-case")
    if data["status"] not in PUBLIC_STATUSES and data["status"] != "draft":
        raise InsightsGenerationError(
            f"{path}: status must be draft, approved, or published"
        )
    if not data["image"].startswith(("/", "https://")):
        raise InsightsGenerationError(f"{path}: image must be an absolute site path or HTTPS URL")
    try:
        date.fromisoformat(data["date"])
    except ValueError as exc:
        raise InsightsGenerationError(f"{path}: date must use YYYY-MM-DD") from exc
    if not body.strip():
        raise InsightsGenerationError(f"{path}: article body must not be empty")

    return Article(path=path, body=body.strip(), **data)


def load_articles(articles_dir: Path = ARTICLES_DIR) -> list[Article]:
    if not articles_dir.exists():
        return []
    articles = [parse_article_file(path) for path in sorted(articles_dir.glob("*.md"))]
    public = [article for article in articles if article.status in PUBLIC_STATUSES]
    by_slug: dict[str, Path] = {}
    for article in public:
        if article.slug in by_slug:
            raise InsightsGenerationError(
                f"duplicate public article slug {article.slug}: "
                f"{by_slug[article.slug]} and {article.path}"
            )
        by_slug[article.slug] = article.path
    return sorted(public, key=lambda article: (article.date, article.slug), reverse=True)


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener">\1</a>',
        escaped,
    )
    escaped = re.sub(r"(https?://[^\s<]+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', escaped)
    return escaped


def flush_paragraph(parts: list[str], output: list[str]) -> None:
    if parts:
        output.append(f"                    <p>{inline_markdown(' '.join(parts))}</p>")
        parts.clear()


def markdown_to_html(markdown: str) -> str:
    output: list[str] = []
    paragraph: list[str] = []
    ordered_items: list[str] = []
    unordered_items: list[str] = []

    def flush_ordered() -> None:
        if ordered_items:
            output.append("                    <ol>")
            for item in ordered_items:
                output.append(f"                        <li>{inline_markdown(item)}</li>")
            output.append("                    </ol>")
            ordered_items.clear()

    def flush_unordered() -> None:
        if unordered_items:
            output.append("                    <ul>")
            for item in unordered_items:
                output.append(f"                        <li>{inline_markdown(item)}</li>")
            output.append("                    </ul>")
            unordered_items.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph(paragraph, output)
            flush_ordered()
            flush_unordered()
            continue
        heading = re.fullmatch(r"(#{2,3})\s+(.+)", line)
        if heading:
            flush_paragraph(paragraph, output)
            flush_ordered()
            flush_unordered()
            tag = "h2" if heading.group(1) == "##" else "h3"
            output.append(f"                    <{tag}>{inline_markdown(heading.group(2))}</{tag}>")
            continue
        ordered = re.fullmatch(r"\d+\.\s+(.+)", line)
        if ordered:
            flush_paragraph(paragraph, output)
            flush_unordered()
            ordered_items.append(ordered.group(1))
            continue
        unordered = re.fullmatch(r"[-*]\s+(.+)", line)
        if unordered:
            flush_paragraph(paragraph, output)
            flush_ordered()
            unordered_items.append(unordered.group(1))
            continue
        flush_ordered()
        flush_unordered()
        paragraph.append(line)

    flush_paragraph(paragraph, output)
    flush_ordered()
    flush_unordered()
    return "\n".join(output)


def render_head(title: str, description: str, canonical_url: str, image_url: str) -> str:
    return f"""    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)}</title>
    <meta name="description" content="{html.escape(description)}">
    <link rel="canonical" href="{html.escape(canonical_url)}">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{html.escape(title)}">
    <meta property="og:description" content="{html.escape(description)}">
    <meta property="og:url" content="{html.escape(canonical_url)}">
    <meta property="og:image" content="{html.escape(image_url)}">
    <meta property="og:site_name" content="Flexity">
    <link rel="icon" href="/assets/favicon.ico" type="image/x-icon">
    <link href="{BOOTSTRAP_CSS}" rel="stylesheet"
        integrity="{BOOTSTRAP_CSS_INTEGRITY}" crossorigin="anonymous">
    <link rel="stylesheet" href="/assets/site.css">"""


def render_nav(active_insights: bool = True) -> str:
    active = " active" if active_insights else ""
    return f"""    <nav class="navbar navbar-expand-lg navbar-dark fixed-top border-bottom border-secondary-subtle">
        <div class="container">
            <a class="navbar-brand d-flex align-items-center gap-2 text-light" href="/">
                <img src="/assets/flexity-logo.svg" alt="Flexity" height="28"><span>FLEXITY</span>
            </a>
            <button class="navbar-toggler text-light border-0" type="button" data-bs-toggle="collapse"
                data-bs-target="#mainNav"><span class="navbar-toggler-icon"></span></button>
            <div class="collapse navbar-collapse" id="mainNav">
                <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                    <li class="nav-item"><a class="nav-link text-light" href="/solutions/">Решения</a></li>
                    <li class="nav-item"><a class="nav-link text-light" href="/services/">Услуги</a></li>
                    <li class="nav-item"><a class="nav-link text-light" href="/diagnostics/free.html">Диагностика</a></li>
                    <li class="nav-item"><a class="nav-link text-light{active}" href="/insights/">Insights</a></li>
                    <li class="nav-item"><a class="nav-link text-light" href="/cases/">Кейсы</a></li>
                    <li class="nav-item"><a class="nav-link text-light" href="/calculators/">Калькуляторы</a></li>
                    <li class="nav-item"><a class="nav-link text-light" href="/demo/">Демо</a></li>
                </ul>
                <div class="d-flex gap-2">
                    <a class="btn btn-outline-light btn-sm" href="https://flexity.asia/console/login">Войти в систему</a>
                    <a class="btn btn-primary btn-sm" href="/diagnostics/free.html">Бесплатная диагностика</a>
                </div>
            </div>
        </div>
    </nav>"""


def render_insights_cta() -> str:
    return """            <div class="contact-card mt-4">
                <h2 class="section-title h4">Не знаете, с чего начать?</h2>
                <p class="mb-3">Не знаете, с чего начать автоматизацию? Начните с бесплатной диагностики — короткий разбор процесса без обязательств.</p>
                <div class="d-flex flex-wrap gap-2">
                    <a class="btn btn-primary" href="/diagnostics/free.html">Бесплатная диагностика</a>
                    <a class="btn btn-outline-light" href="/demo/">Запросить демо</a>
                </div>
            </div>"""


def render_footer() -> str:
    return f"""    <footer>
        <div class="container"><span>© <span id="year"></span> Flexity</span></div>
    </footer>
    <script>document.getElementById('year').textContent = new Date().getFullYear();</script>
    <script src="{BOOTSTRAP_JS}"
        integrity="{BOOTSTRAP_JS_INTEGRITY}" crossorigin="anonymous"></script>"""


def render_index(articles: list[Article]) -> str:
    description = (
        "Материалы Flexity о CRM, учёте, AI и автоматизации для владельцев "
        "и операционных директоров."
    )
    cards = []
    for article in articles:
        cards.append(
            f"""                <article class="card-module p-4 h-100">
                    <div class="badge-soft mb-3">{html.escape(article.category)}</div>
                    <h2 class="section-title h4 mb-2">
                        <a href="{html.escape(article.url_path)}">{html.escape(article.title)}</a>
                    </h2>
                    <p class="small text-secondary mb-2">{html.escape(article.date)}</p>
                    <p class="mb-3">{html.escape(article.description)}</p>
                    <a class="btn btn-sm btn-primary" href="{html.escape(article.url_path)}">Читать материал</a>
                </article>"""
        )
    article_grid = "\n".join(
        f"""            <div class="col-md-6">
{card}
            </div>"""
        for card in cards
    )
    if not article_grid:
        article_grid = """            <div class="col-12">
                <div class="contact-card">
                    <p class="mb-0 text-secondary">Публикации готовятся.</p>
                </div>
            </div>"""

    return f"""<!DOCTYPE html>
<html lang="ru">

<head>
{render_head("Insights — Flexity", description, f"{SITE_ORIGIN}/insights/", f"{SITE_ORIGIN}/assets/flexity-logo.svg")}
</head>

<body>
{render_nav()}

    <main class="page-hero">
        <div class="container">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="/">Главная</a></li>
                    <li class="breadcrumb-item active">Insights</li>
                </ol>
            </nav>
            <div class="badge-soft mb-3">Контент-хаб</div>
            <h1 class="page-title mb-3">Insights</h1>
            <p class="page-lead mb-4">{html.escape(description)}</p>

            <div class="row g-4">
{article_grid}
            </div>

{render_insights_cta()}
        </div>
    </main>

{render_footer()}
</body>

</html>
"""


def render_article(article: Article) -> str:
    body_html = markdown_to_html(article.body)
    return f"""<!DOCTYPE html>
<html lang="ru">

<head>
{render_head(f"{article.title} — Flexity", article.description, article.canonical_url, article.image_url)}
</head>

<body>
{render_nav()}

    <main class="page-hero">
        <article class="container">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="/">Главная</a></li>
                    <li class="breadcrumb-item"><a href="/insights/">Insights</a></li>
                    <li class="breadcrumb-item active">{html.escape(article.title)}</li>
                </ol>
            </nav>
            <div class="badge-soft mb-3">{html.escape(article.category)}</div>
            <h1 class="page-title mb-3">{html.escape(article.title)}</h1>
            <p class="page-lead mb-3">{html.escape(article.description)}</p>
            <p class="small text-secondary mb-4">
                {html.escape(article.date)} · Источник: {html.escape(article.source)}
            </p>
            <img class="img-fluid rounded mb-4" src="{html.escape(article.image)}" alt="{html.escape(article.title)}">
            <div class="contact-card mb-4">
{body_html}
            </div>
            <div class="contact-card">
                <h2 class="section-title h4">Не знаете, с чего начать?</h2>
                <p class="mb-3">Не знаете, с чего начать автоматизацию? Начните с бесплатной диагностики — короткий разбор процесса без обязательств.</p>
                <div class="d-flex flex-wrap gap-2">
                    <a class="btn btn-primary" href="/diagnostics/free.html">Бесплатная диагностика</a>
                    <a class="btn btn-outline-light" href="/demo/">Запросить демо</a>
                </div>
            </div>
        </article>
    </main>

{render_footer()}
</body>

</html>
"""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def generate_insights(
    articles_dir: Path = ARTICLES_DIR,
    output_dir: Path = INSIGHTS_DIR,
) -> list[Path]:
    articles = load_articles(articles_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    index_path = output_dir / "index.html"
    write_text(index_path, render_index(articles))
    written.append(index_path)

    for article in articles:
        article_path = output_dir / f"{article.slug}.html"
        write_text(article_path, render_article(article))
        written.append(article_path)

    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate static Flexity insights pages from approved articles."
    )
    parser.add_argument(
        "--articles-dir",
        default=str(ARTICLES_DIR),
        help="Directory containing article markdown files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(INSIGHTS_DIR),
        help="Directory where static insights HTML files are written.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        written = generate_insights(Path(args.articles_dir), Path(args.output_dir))
    except (OSError, InsightsGenerationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for path in written:
        print(f"GENERATED {path}")
    print(f"Done. Generated: {len(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
