from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import yaml


SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "content"
    / "publish_instagram_live.py"
)
SCRIPT_DIR = SCRIPT_PATH.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

SPEC = importlib.util.spec_from_file_location("publish_instagram_live", SCRIPT_PATH)
assert SPEC and SPEC.loader
publish_instagram_live = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish_instagram_live)


class InstagramLivePublisherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.content_dir = Path(self.temporary_directory.name)
        self.now = datetime(2026, 6, 23, 8, 0, tzinfo=timezone.utc)
        self.environment = {
            "INSTAGRAM_USER_ID": "123456789",
            "INSTAGRAM_ACCESS_TOKEN": "test-token-secret-abc",
        }

    def create_pack(
        self,
        name: str = "test-pack",
        *,
        pack_status: str = "approved",
        instagram_status: str = "approved",
        post_type: str = "feed_image",
        publish_at: str = "2026-06-23T10:00:00+05:00",
        published_at: str | None = None,
        external_id: str | None = None,
        image_url: str = "https://cdn.example.com/post.jpg",
        video_url: str = "https://cdn.example.com/reel.mp4",
        media: dict | None = None,
        caption_source: str = "instagram.md",
        caption: str = "Approved caption",
    ) -> Path:
        pack_dir = self.content_dir / name
        pack_dir.mkdir()
        pack = {
            "date": "2026-06-23",
            "topic": "Test",
            "slug": name,
            "status": pack_status,
        }
        (pack_dir / "pack.yml").write_text(
            yaml.safe_dump(pack, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        media_payload = media if media is not None else {"image_url": image_url}
        if post_type == "reels" and media is None:
            media_payload = {"video_url": video_url}
        instagram = {
            "status": instagram_status,
            "type": post_type,
            "publish_at": publish_at,
            "published_at": published_at,
            "external_id": external_id,
            "media": media_payload,
            "caption_source": caption_source,
        }
        (pack_dir / "instagram.yml").write_text(
            yaml.safe_dump(instagram, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (pack_dir / "instagram.md").write_text(caption, encoding="utf-8")
        (pack_dir / "publish_log.yml").write_text("events: []\n", encoding="utf-8")
        return pack_dir

    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = publish_instagram_live.main(
                argv,
                self.content_dir,
                self.now,
                self.environment,
            )
        return result, stdout.getvalue(), stderr.getvalue()

    def assert_token_absent(self, *texts: str) -> None:
        token = self.environment["INSTAGRAM_ACCESS_TOKEN"]
        for text in texts:
            self.assertNotIn(token, text)

    def test_approved_pack_publishes_when_all_gates_pass(self) -> None:
        pack_dir = self.create_pack()
        create_response = Mock(status_code=200)
        create_response.json.return_value = {"id": "creation-123"}
        publish_response = Mock(status_code=200)
        publish_response.json.return_value = {"id": "media-456"}

        with patch.object(
            publish_instagram_live.requests, "post", side_effect=[create_response, publish_response]
        ) as post:
            result, stdout, stderr = self.run_main(["--live"])

        self.assertEqual(result, 0)
        self.assertIn("PUBLISHED test-pack: external_id=media-456", stdout)
        self.assertEqual(post.call_count, 2)
        self.assert_token_absent(stdout, stderr)

        saved = publish_instagram_live.load_yaml(pack_dir / "instagram.yml")
        self.assertEqual(saved["status"], "published")
        self.assertEqual(saved["external_id"], "media-456")
        self.assertIsNotNone(saved["published_at"])
        log = publish_instagram_live.load_yaml(pack_dir / "publish_log.yml")
        self.assertEqual(log["events"][-1]["status"], "published")
        self.assertEqual(log["events"][-1]["external_id"], "media-456")
        self.assert_token_absent(yaml.safe_dump(log))

    def test_draft_instagram_pack_is_skipped(self) -> None:
        self.create_pack(instagram_status="draft")
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, stdout, stderr = self.run_main(["--live"])
        self.assertEqual(result, 0)
        post.assert_not_called()
        self.assertIn("SKIP test-pack: status is not approved", stdout)
        self.assert_token_absent(stdout, stderr)

    def test_draft_pack_yml_is_skipped(self) -> None:
        self.create_pack(pack_status="draft")
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, stdout, stderr = self.run_main(["--live"])
        self.assertEqual(result, 0)
        post.assert_not_called()
        self.assertIn("SKIP test-pack: pack.status is not approved", stdout)
        self.assert_token_absent(stdout, stderr)

    def test_already_published_pack_is_skipped(self) -> None:
        self.create_pack(
            published_at="2026-06-23T10:01:00+05:00",
        )
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, stdout, stderr = self.run_main(["--live"])
        self.assertEqual(result, 0)
        post.assert_not_called()
        self.assertIn("SKIP test-pack: already published", stdout)
        self.assert_token_absent(stdout, stderr)

    def test_external_id_already_set_is_skipped(self) -> None:
        self.create_pack(external_id="media-existing")
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, stdout, stderr = self.run_main(["--live"])
        self.assertEqual(result, 0)
        post.assert_not_called()
        self.assertIn("SKIP test-pack: already published", stdout)

    def test_missing_access_token_fails_closed(self) -> None:
        self.create_pack()
        environment = {
            "INSTAGRAM_USER_ID": "123456789",
        }
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(publish_instagram_live.requests, "post") as post:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = publish_instagram_live.main(
                    ["--live"],
                    self.content_dir,
                    self.now,
                    environment,
                )
        self.assertEqual(result, 1)
        post.assert_not_called()
        self.assertIn("INSTAGRAM_ACCESS_TOKEN is not set", stderr.getvalue())

    def test_missing_user_id_fails_closed(self) -> None:
        self.create_pack()
        environment = {
            "INSTAGRAM_ACCESS_TOKEN": "test-token-secret-abc",
        }
        stderr = io.StringIO()
        with patch.object(publish_instagram_live.requests, "post") as post:
            with redirect_stderr(stderr):
                result = publish_instagram_live.main(
                    ["--live"],
                    self.content_dir,
                    self.now,
                    environment,
                )
        self.assertEqual(result, 1)
        post.assert_not_called()
        self.assertIn("INSTAGRAM_USER_ID is not set", stderr.getvalue())

    def test_invalid_http_image_url_fails_closed(self) -> None:
        self.create_pack(image_url="http://cdn.example.com/post.jpg")
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, _, stderr = self.run_main(["--live"])
        self.assertEqual(result, 1)
        post.assert_not_called()
        self.assertIn("media.image_url must start with https://", stderr)

    def test_missing_image_url_fails_closed(self) -> None:
        self.create_pack(image_url="")
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, _, stderr = self.run_main(["--live"])
        self.assertEqual(result, 1)
        post.assert_not_called()
        self.assertIn("media.image_url is required", stderr)

    def test_missing_caption_source_fails_closed(self) -> None:
        pack_dir = self.create_pack()
        config = publish_instagram_live.load_yaml(pack_dir / "instagram.yml")
        del config["caption_source"]
        publish_instagram_live.save_yaml(pack_dir / "instagram.yml", config)
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, _, stderr = self.run_main(["--live"])
        self.assertEqual(result, 1)
        post.assert_not_called()
        self.assertIn("caption_source is required", stderr)

    def test_unsupported_type_fails_closed(self) -> None:
        self.create_pack(post_type="story")
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, _, stderr = self.run_main(["--live"])
        self.assertEqual(result, 1)
        post.assert_not_called()
        self.assertIn("type must be one of", stderr)

    def test_api_container_error_does_not_mark_published(self) -> None:
        pack_dir = self.create_pack()
        response = Mock(status_code=400)
        response.json.return_value = {
            "error": {"message": "Invalid parameter", "code": 100}
        }
        with patch.object(publish_instagram_live.requests, "post", return_value=response):
            result, _, stderr = self.run_main(["--live"])
        self.assertEqual(result, 1)
        saved = publish_instagram_live.load_yaml(pack_dir / "instagram.yml")
        self.assertIsNone(saved["published_at"])
        self.assertIsNone(saved["external_id"])
        self.assertEqual(saved["status"], "approved")
        log = publish_instagram_live.load_yaml(pack_dir / "publish_log.yml")
        self.assertEqual(log["events"][-1]["status"], "error")
        self.assert_token_absent(stderr, log["events"][-1]["error"])

    def test_api_publish_error_does_not_mark_published(self) -> None:
        pack_dir = self.create_pack()
        create_response = Mock(status_code=200)
        create_response.json.return_value = {"id": "creation-123"}
        publish_response = Mock(status_code=400)
        publish_response.json.return_value = {
            "error": {"message": "Publish failed", "code": 9007}
        }
        with patch.object(
            publish_instagram_live.requests,
            "post",
            side_effect=[create_response, publish_response],
        ):
            result, _, stderr = self.run_main(["--live"])
        self.assertEqual(result, 1)
        saved = publish_instagram_live.load_yaml(pack_dir / "instagram.yml")
        self.assertIsNone(saved["published_at"])
        self.assertIsNone(saved["external_id"])
        self.assertEqual(saved["status"], "approved")
        log = publish_instagram_live.load_yaml(pack_dir / "publish_log.yml")
        self.assertEqual(log["events"][-1]["status"], "error")
        self.assert_token_absent(stderr, log["events"][-1]["error"])

    def test_successful_publish_does_not_modify_pack_yml_or_caption(self) -> None:
        pack_dir = self.create_pack()
        pack_before = (pack_dir / "pack.yml").read_bytes()
        caption_before = (pack_dir / "instagram.md").read_bytes()
        create_response = Mock(status_code=200)
        create_response.json.return_value = {"id": "creation-123"}
        publish_response = Mock(status_code=200)
        publish_response.json.return_value = {"id": "media-456"}
        with patch.object(
            publish_instagram_live.requests,
            "post",
            side_effect=[create_response, publish_response],
        ):
            self.run_main(["--live"])
        self.assertEqual((pack_dir / "pack.yml").read_bytes(), pack_before)
        self.assertEqual((pack_dir / "instagram.md").read_bytes(), caption_before)

    def test_default_dry_run_writes_nothing_and_calls_no_api(self) -> None:
        pack_dir = self.create_pack()
        instagram_before = (pack_dir / "instagram.yml").read_bytes()
        log_before = (pack_dir / "publish_log.yml").read_bytes()
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, stdout, stderr = self.run_main([])
        self.assertEqual(result, 0)
        post.assert_not_called()
        self.assertIn("would_publish=true", stdout)
        self.assertEqual((pack_dir / "instagram.yml").read_bytes(), instagram_before)
        self.assertEqual((pack_dir / "publish_log.yml").read_bytes(), log_before)
        self.assert_token_absent(stdout, stderr)

    def test_dry_run_does_not_require_secrets(self) -> None:
        self.create_pack()
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, stdout, stderr = self.run_main_with_env({})
        self.assertEqual(result, 0)
        post.assert_not_called()
        self.assertIn("would_publish=true", stdout)
        self.assert_token_absent(stdout, stderr)

    def run_main_with_env(self, environment: dict[str, str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = publish_instagram_live.main(
                [],
                self.content_dir,
                self.now,
                environment,
            )
        return result, stdout.getvalue(), stderr.getvalue()

    def test_reels_publishes_when_video_url_present(self) -> None:
        self.create_pack(post_type="reels")
        create_response = Mock(status_code=200)
        create_response.json.return_value = {"id": "creation-reel"}
        publish_response = Mock(status_code=200)
        publish_response.json.return_value = {"id": "reel-media"}
        with patch.object(
            publish_instagram_live.requests, "post", side_effect=[create_response, publish_response]
        ):
            result, stdout, _ = self.run_main(["--live"])
        self.assertEqual(result, 0)
        self.assertIn("PUBLISHED test-pack: external_id=reel-media", stdout)

    def test_reels_without_video_url_fails_closed(self) -> None:
        self.create_pack(post_type="reels", media={"video_url": ""})
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, _, stderr = self.run_main(["--live"])
        self.assertEqual(result, 1)
        post.assert_not_called()
        self.assertIn("media.video_url is required", stderr)

    def test_carousel_publishes_with_two_items(self) -> None:
        self.create_pack(
            post_type="carousel",
            media={
                "items": [
                    {"image_url": "https://cdn.example.com/slide-1.jpg"},
                    {"image_url": "https://cdn.example.com/slide-2.jpg"},
                ]
            },
        )
        child1 = Mock(status_code=200)
        child1.json.return_value = {"id": "child-1"}
        child2 = Mock(status_code=200)
        child2.json.return_value = {"id": "child-2"}
        parent = Mock(status_code=200)
        parent.json.return_value = {"id": "parent-carousel"}
        publish = Mock(status_code=200)
        publish.json.return_value = {"id": "carousel-media"}
        with patch.object(
            publish_instagram_live.requests,
            "post",
            side_effect=[child1, child2, parent, publish],
        ):
            result, stdout, _ = self.run_main(["--live"])
        self.assertEqual(result, 0)
        self.assertIn("PUBLISHED test-pack: external_id=carousel-media", stdout)

    def test_carousel_child_create_error_fails_closed(self) -> None:
        self.create_pack(
            post_type="carousel",
            media={
                "items": [
                    {"image_url": "https://cdn.example.com/slide-1.jpg"},
                    {"image_url": "https://cdn.example.com/slide-2.jpg"},
                ]
            },
        )
        bad = Mock(status_code=400)
        bad.json.return_value = {"error": {"message": "Invalid child", "code": 100}}
        with patch.object(publish_instagram_live.requests, "post", side_effect=[bad]):
            result, _, stderr = self.run_main(["--live"])
        self.assertEqual(result, 1)
        self.assertIn("media container creation", stderr)

    def test_carousel_requires_two_items(self) -> None:
        self.create_pack(post_type="carousel", media={"items": [{"image_url": "https://cdn.example.com/one.jpg"}]})
        with patch.object(publish_instagram_live.requests, "post") as post:
            result, _, stderr = self.run_main(["--live"])
        self.assertEqual(result, 1)
        post.assert_not_called()
        self.assertIn("at least 2 items", stderr)


if __name__ == "__main__":
    unittest.main()
