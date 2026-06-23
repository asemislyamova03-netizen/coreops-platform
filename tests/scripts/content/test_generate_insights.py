from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "content"
    / "generate_insights.py"
)
SPEC = importlib.util.spec_from_file_location("generate_insights", SCRIPT_PATH)
assert SPEC and SPEC.loader
generate_insights = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = generate_insights
SPEC.loader.exec_module(generate_insights)


class InsightsGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.articles_dir = self.root / "landing" / "content" / "articles"
        self.output_dir = self.root / "landing" / "www" / "insights"
        self.articles_dir.mkdir(parents=True)

    def write_article(
        self,
        name: str = "2026-06-23-test.md",
        *,
        slug: str = "test-article",
        status: str = "approved",
        extra_frontmatter: str = "",
        omit: str | None = None,
        body: str = "## Заголовок\n\nТекст статьи.\n",
    ) -> Path:
        fields = {
            "title": "Тестовая статья",
            "date": "2026-06-23",
            "category": "AI для бизнеса",
            "slug": slug,
            "status": status,
            "description": "Краткое описание статьи.",
            "source": "test",
            "cta": "Разобрать процесс можно через демо.",
            "image": "/assets/social/test/instagram-feed.png",
        }
        if omit:
            del fields[omit]
        frontmatter = "\n".join(f'{key}: "{value}"' for key, value in fields.items())
        if extra_frontmatter:
            frontmatter = f"{frontmatter}\n{extra_frontmatter}"
        path = self.articles_dir / name
        path.write_text(f"---\n{frontmatter}\n---\n\n{body}", encoding="utf-8")
        return path

    def test_generates_index_and_article_for_approved_article(self) -> None:
        self.write_article()

        written = generate_insights.generate_insights(
            self.articles_dir, self.output_dir
        )

        index_path = self.output_dir / "index.html"
        article_path = self.output_dir / "test-article.html"
        self.assertEqual(written, [index_path, article_path])
        self.assertTrue(index_path.is_file())
        self.assertTrue(article_path.is_file())
        index_html = index_path.read_text(encoding="utf-8")
        article_html = article_path.read_text(encoding="utf-8")
        self.assertIn("Тестовая статья", index_html)
        self.assertIn('/insights/test-article.html', index_html)
        self.assertIn('<meta property="og:title"', article_html)
        self.assertIn("https://www.flexity.asia/insights/test-article.html", article_html)
        self.assertIn('<h2>Заголовок</h2>', article_html)

    def test_published_article_is_public(self) -> None:
        self.write_article(status="published")
        written = generate_insights.generate_insights(
            self.articles_dir, self.output_dir
        )
        self.assertIn(self.output_dir / "test-article.html", written)

    def test_draft_article_is_skipped(self) -> None:
        self.write_article(status="draft")
        written = generate_insights.generate_insights(
            self.articles_dir, self.output_dir
        )
        self.assertEqual(written, [self.output_dir / "index.html"])
        self.assertFalse((self.output_dir / "test-article.html").exists())

    def test_missing_required_frontmatter_fails_closed(self) -> None:
        self.write_article(omit="description")
        with self.assertRaisesRegex(
            generate_insights.InsightsGenerationError,
            "missing required frontmatter fields: description",
        ):
            generate_insights.generate_insights(self.articles_dir, self.output_dir)

    def test_duplicate_public_slug_fails_closed(self) -> None:
        self.write_article("one.md", slug="same-slug")
        self.write_article("two.md", slug="same-slug")
        with self.assertRaisesRegex(
            generate_insights.InsightsGenerationError,
            "duplicate public article slug same-slug",
        ):
            generate_insights.generate_insights(self.articles_dir, self.output_dir)

    def test_duplicate_draft_slug_does_not_block_public_article(self) -> None:
        self.write_article("one.md", slug="same-slug")
        self.write_article("two.md", slug="same-slug", status="draft")
        written = generate_insights.generate_insights(
            self.articles_dir, self.output_dir
        )
        self.assertIn(self.output_dir / "same-slug.html", written)

    def test_invalid_slug_fails_closed(self) -> None:
        self.write_article(slug="Bad Slug")
        with self.assertRaisesRegex(
            generate_insights.InsightsGenerationError,
            "slug must be lowercase kebab-case",
        ):
            generate_insights.generate_insights(self.articles_dir, self.output_dir)

    def test_invalid_status_fails_closed(self) -> None:
        self.write_article(status="ready")
        with self.assertRaisesRegex(
            generate_insights.InsightsGenerationError,
            "status must be draft, approved, or published",
        ):
            generate_insights.generate_insights(self.articles_dir, self.output_dir)


if __name__ == "__main__":
    unittest.main()
