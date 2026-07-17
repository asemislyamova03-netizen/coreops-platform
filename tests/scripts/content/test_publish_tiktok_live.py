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


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "content" / "publish_tiktok_live.py"
SCRIPT_DIR = SCRIPT_PATH.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("publish_tiktok_live", SCRIPT_PATH)
assert SPEC and SPEC.loader
publish_tiktok_live = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish_tiktok_live)


class TikTokLivePublisherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.content_dir = Path(self.tmp.name)
        self.now = datetime(2026, 6, 23, 8, 0, tzinfo=timezone.utc)
        self.env = {"TIKTOK_ACCESS_TOKEN": "tiktok-secret-token-abc"}

    def create_pack(self, *, status: str = "approved", video_url: str = "https://cdn.example.com/video.mp4") -> Path:
        pack_dir = self.content_dir / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "pack.yml").write_text(yaml.safe_dump({"status": "approved"}, sort_keys=False), encoding="utf-8")
        tiktok = {
            "status": status,
            "type": "video",
            "publish_at": "2026-06-23T10:00:00+05:00",
            "published_at": None,
            "external_id": None,
            "caption_source": "tiktok.md",
            "media": {"video_url": video_url},
        }
        (pack_dir / "tiktok.yml").write_text(yaml.safe_dump(tiktok, sort_keys=False), encoding="utf-8")
        (pack_dir / "tiktok.md").write_text("TikTok caption", encoding="utf-8")
        (pack_dir / "publish_log.yml").write_text("events: []\n", encoding="utf-8")
        return pack_dir

    def run_main(self, argv: list[str], environment: dict[str, str] | None = None) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = publish_tiktok_live.main(
                argv,
                self.content_dir,
                self.now,
                environment if environment is not None else self.env,
            )
        return code, out.getvalue(), err.getvalue()

    def assert_token_absent(self, *texts: str) -> None:
        token = self.env["TIKTOK_ACCESS_TOKEN"]
        for text in texts:
            self.assertNotIn(token, text)
            self.assertNotIn("Bearer tiktok-secret", text)
            self.assertNotIn("access_token=tiktok-secret", text)

    def test_dry_run_video_does_not_call_external_apis(self) -> None:
        pack_dir = self.create_pack()
        before = (pack_dir / "tiktok.yml").read_bytes()
        with patch.object(publish_tiktok_live.requests, "post") as post, patch.object(
            publish_tiktok_live.requests, "get"
        ) as get, patch.object(publish_tiktok_live.requests, "request") as request:
            code, out, err = self.run_main([])
        self.assertEqual(code, 0)
        post.assert_not_called()
        get.assert_not_called()
        request.assert_not_called()
        self.assertIn("WOULD_PUBLISH pack=test-pack type=video", out)
        self.assertEqual(err, "")
        self.assertEqual((pack_dir / "tiktok.yml").read_bytes(), before)
        self.assert_token_absent(out, err)

    def test_dry_run_does_not_require_secrets(self) -> None:
        self.create_pack()
        with patch.object(publish_tiktok_live.requests, "post") as post:
            code, out, err = self.run_main([], environment={})
        self.assertEqual(code, 0)
        post.assert_not_called()
        self.assertIn("would_publish=true", out)
        self.assert_token_absent(out, err)

    def test_live_without_experimental_gate_fails_closed(self) -> None:
        self.create_pack()
        with patch.object(publish_tiktok_live.requests, "post") as post:
            code, out, err = self.run_main(["--live"])
        self.assertEqual(code, 1)
        post.assert_not_called()
        self.assertIn("fail-closed", err)
        self.assertIn("NOT supported yet", err)
        self.assertEqual(out, "")
        self.assert_token_absent(out, err)

    def test_live_publish_video_with_experimental_flag(self) -> None:
        pack_dir = self.create_pack()
        response = Mock(status_code=200)
        response.json.return_value = {"data": {"publish_id": "tt-1"}}
        with patch.object(publish_tiktok_live.requests, "post", return_value=response) as post:
            code, out, err = self.run_main(["--live", "--allow-experimental-live"])
        self.assertEqual(code, 0)
        self.assertEqual(post.call_count, 1)
        self.assertIn("PUBLISHED test-pack: external_id=tt-1", out)
        self.assertEqual(err, "")
        saved = publish_tiktok_live.load_yaml(pack_dir / "tiktok.yml")
        self.assertEqual(saved["status"], "published")
        self.assert_token_absent(out, err)

    def test_live_publish_video_with_experimental_env(self) -> None:
        self.create_pack()
        response = Mock(status_code=200)
        response.json.return_value = {"data": {"publish_id": "tt-env"}}
        env = {
            **self.env,
            publish_tiktok_live.EXPERIMENTAL_LIVE_ENV: "1",
        }
        with patch.object(publish_tiktok_live.requests, "post", return_value=response):
            code, out, err = self.run_main(["--live"], environment=env)
        self.assertEqual(code, 0)
        self.assertIn("PUBLISHED test-pack: external_id=tt-env", out)
        self.assert_token_absent(out, err)

    def test_invalid_video_url_fails_closed(self) -> None:
        self.create_pack(video_url="http://cdn.example.com/video.mp4")
        with patch.object(publish_tiktok_live.requests, "post") as post:
            code, _, err = self.run_main(["--live", "--allow-experimental-live"])
        self.assertEqual(code, 1)
        post.assert_not_called()
        self.assertIn("media.video_url must start with https://", err)

    def test_sanitize_error_redacts_bearer_authorization_and_access_token(self) -> None:
        self.assertEqual(
            publish_tiktok_live.sanitize_error("prefix Bearer tiktok-secret-token-abc suffix"),
            "prefix Bearer [REDACTED] suffix",
        )
        self.assertEqual(
            publish_tiktok_live.sanitize_error("Authorization: tiktok-secret-token-abc"),
            "Authorization: [REDACTED]",
        )
        self.assertEqual(
            publish_tiktok_live.sanitize_error("access_token=tiktok-secret-token-abc&x=1"),
            "access_token=[REDACTED]&x=1",
        )
        combined = publish_tiktok_live.sanitize_error(
            "HTTP 401 Authorization: Bearer tiktok-secret-token-abc "
            "access_token=tiktok-secret-token-abc"
        )
        self.assertNotIn("tiktok-secret-token-abc", combined)
        self.assertIn("[REDACTED]", combined)

    def test_api_error_path_does_not_leak_secrets(self) -> None:
        pack_dir = self.create_pack()
        response = Mock(status_code=401)
        response.json.return_value = {
            "error": {
                "message": (
                    "Unauthorized Authorization: Bearer tiktok-secret-token-abc "
                    "access_token=tiktok-secret-token-abc"
                )
            }
        }
        with patch.object(publish_tiktok_live.requests, "post", return_value=response):
            code, out, err = self.run_main(["--live", "--allow-experimental-live"])
        self.assertEqual(code, 1)
        log = publish_tiktok_live.load_yaml(pack_dir / "publish_log.yml")
        error_text = log["events"][-1]["error"]
        self.assertEqual(log["events"][-1]["status"], "error")
        self.assert_token_absent(out, err, error_text)
        self.assertIn("[REDACTED]", error_text)

    def test_cli_help_states_production_live_not_supported(self) -> None:
        help_text = publish_tiktok_live.build_parser().format_help()
        self.assertIn("NOT supported yet", help_text)
        self.assertIn("--allow-experimental-live", help_text)
        self.assertIn(publish_tiktok_live.EXPERIMENTAL_LIVE_ENV, help_text)


if __name__ == "__main__":
    unittest.main()
