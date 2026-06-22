from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

import yaml


SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "content" / "publish_instagram.py"
)
SPEC = importlib.util.spec_from_file_location("publish_instagram", SCRIPT_PATH)
assert SPEC and SPEC.loader
publish_instagram = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish_instagram)


class InstagramDryRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.content_dir = Path(self.temporary_directory.name)
        self.now = datetime(2026, 6, 23, 8, 0, tzinfo=timezone.utc)

    def create_pack(
        self,
        name: str = "test-pack",
        *,
        status: str = "approved",
        post_type: str = "feed_image",
        publish_at: str = "2026-06-23T10:00:00+05:00",
        published_at: str | None = None,
        media: dict | None = None,
        caption: str = "Approved caption",
    ) -> Path:
        pack_dir = self.content_dir / name
        pack_dir.mkdir()
        config = {
            "status": status,
            "type": post_type,
            "publish_at": publish_at,
            "published_at": published_at,
            "external_id": None,
            "media": media if media is not None else {},
            "caption_source": "instagram.md",
        }
        (pack_dir / "instagram.yml").write_text(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (pack_dir / "instagram.md").write_text(caption, encoding="utf-8")
        return pack_dir

    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = publish_instagram.main(argv, self.content_dir, self.now)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_approved_feed_image_with_url_would_publish(self) -> None:
        pack_dir = self.create_pack(
            media={"image_url": "https://cdn.example.com/post.jpg"}
        )
        config_before = (pack_dir / "instagram.yml").read_bytes()
        caption_before = (pack_dir / "instagram.md").read_bytes()

        result, stdout, stderr = self.run_main(["--dry-run"])

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertIn("pack=test-pack", stdout)
        self.assertIn("type=feed_image", stdout)
        self.assertIn("caption_length=16", stdout)
        self.assertIn("media_url=https://cdn.example.com/post.jpg", stdout)
        self.assertIn("would_publish=true", stdout)
        self.assertEqual((pack_dir / "instagram.yml").read_bytes(), config_before)
        self.assertEqual((pack_dir / "instagram.md").read_bytes(), caption_before)

    def test_approved_feed_image_without_url_fails_closed(self) -> None:
        self.create_pack(media={"image_url": None})

        result, stdout, stderr = self.run_main(["--dry-run"])

        self.assertEqual(result, 1)
        self.assertIn("Would publish: 0", stdout)
        self.assertIn("media.image_url is required", stderr)

    def test_draft_post_is_skipped(self) -> None:
        self.create_pack(
            status="draft", media={"image_url": "https://cdn.example.com/post.jpg"}
        )

        result, stdout, stderr = self.run_main(["--dry-run"])

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertIn("SKIP test-pack: status is not approved", stdout)

    def test_already_published_post_is_skipped(self) -> None:
        self.create_pack(
            published_at="2026-06-23T10:01:00+05:00",
            media={"image_url": "https://cdn.example.com/post.jpg"},
        )

        result, stdout, stderr = self.run_main(["--dry-run"])

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertIn("SKIP test-pack: already published", stdout)

    def test_future_post_is_skipped(self) -> None:
        self.create_pack(
            publish_at="2026-06-23T14:00:00+05:00",
            media={"image_url": "https://cdn.example.com/post.jpg"},
        )

        result, stdout, stderr = self.run_main(["--dry-run"])

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertIn("SKIP test-pack: publish_at is in the future", stdout)

    def test_reels_requires_video_url(self) -> None:
        self.create_pack(post_type="reels", media={"video_url": None})

        result, _, stderr = self.run_main(["--dry-run"])

        self.assertEqual(result, 1)
        self.assertIn("media.video_url is required", stderr)

    def test_carousel_with_items_would_publish(self) -> None:
        self.create_pack(
            post_type="carousel",
            media={
                "items": [
                    {"image_url": "https://cdn.example.com/one.jpg"},
                    {"video_url": "https://cdn.example.com/two.mp4"},
                ]
            },
        )

        result, stdout, stderr = self.run_main(["--dry-run"])

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertIn("type=carousel", stdout)
        self.assertIn("https://cdn.example.com/one.jpg", stdout)
        self.assertIn("https://cdn.example.com/two.mp4", stdout)

    def test_carousel_without_items_fails_closed(self) -> None:
        self.create_pack(post_type="carousel", media={"items": []})

        result, _, stderr = self.run_main(["--dry-run"])

        self.assertEqual(result, 1)
        self.assertIn("media.items must be a non-empty list", stderr)

    def test_unsupported_type_fails_closed(self) -> None:
        self.create_pack(
            post_type="story", media={"image_url": "https://cdn.example.com/post.jpg"}
        )

        result, _, stderr = self.run_main(["--dry-run"])

        self.assertEqual(result, 1)
        self.assertIn("type must be one of", stderr)

    def test_publish_at_without_timezone_fails_closed(self) -> None:
        self.create_pack(
            publish_at="2026-06-23T10:00:00",
            media={"image_url": "https://cdn.example.com/post.jpg"},
        )

        result, _, stderr = self.run_main(["--dry-run"])

        self.assertEqual(result, 1)
        self.assertIn("publish_at must include a timezone", stderr)

    def test_empty_caption_fails_closed(self) -> None:
        self.create_pack(
            media={"image_url": "https://cdn.example.com/post.jpg"}, caption="  \n"
        )

        result, _, stderr = self.run_main(["--dry-run"])

        self.assertEqual(result, 1)
        self.assertIn("caption source is empty", stderr)

    def test_without_dry_run_live_path_is_rejected(self) -> None:
        result, _, stderr = self.run_main([])

        self.assertEqual(result, 2)
        self.assertEqual(stderr.strip(), publish_instagram.LIVE_NOT_IMPLEMENTED)


if __name__ == "__main__":
    unittest.main()
