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
        self.env = {"TIKTOK_ACCESS_TOKEN": "secret"}

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

    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = publish_tiktok_live.main(argv, self.content_dir, self.now, self.env)
        return code, out.getvalue(), err.getvalue()

    def test_dry_run_video(self) -> None:
        self.create_pack()
        code, out, err = self.run_main([])
        self.assertEqual(code, 0)
        self.assertIn("WOULD_PUBLISH pack=test-pack type=video", out)
        self.assertEqual(err, "")

    def test_live_publish_video(self) -> None:
        pack_dir = self.create_pack()
        response = Mock(status_code=200)
        response.json.return_value = {"data": {"publish_id": "tt-1"}}
        with patch.object(publish_tiktok_live.requests, "post", return_value=response):
            code, out, err = self.run_main(["--live"])
        self.assertEqual(code, 0)
        self.assertIn("PUBLISHED test-pack: external_id=tt-1", out)
        self.assertEqual(err, "")
        saved = publish_tiktok_live.load_yaml(pack_dir / "tiktok.yml")
        self.assertEqual(saved["status"], "published")

    def test_invalid_video_url_fails_closed(self) -> None:
        self.create_pack(video_url="http://cdn.example.com/video.mp4")
        code, _, err = self.run_main(["--live"])
        self.assertEqual(code, 1)
        self.assertIn("media.video_url must start with https://", err)


if __name__ == "__main__":
    unittest.main()
