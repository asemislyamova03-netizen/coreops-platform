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


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "content" / "publish_threads_live.py"
SCRIPT_DIR = SCRIPT_PATH.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("publish_threads_live", SCRIPT_PATH)
assert SPEC and SPEC.loader
publish_threads_live = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish_threads_live)


class ThreadsLivePublisherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.content_dir = Path(self.tmp.name)
        self.now = datetime(2026, 6, 23, 8, 0, tzinfo=timezone.utc)
        self.env = {
            "THREADS_USER_ID": "123",
            "THREADS_ACCESS_TOKEN": "secret",
        }

    def create_pack(self, *, post_type: str = "text", status: str = "approved") -> Path:
        pack_dir = self.content_dir / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "pack.yml").write_text(yaml.safe_dump({"status": "approved"}, sort_keys=False), encoding="utf-8")
        threads = {
            "status": status,
            "type": post_type,
            "publish_at": "2026-06-23T10:00:00+05:00",
            "published_at": None,
            "external_id": None,
            "caption_source": "threads.md",
            "media": {"image_url": "https://cdn.example.com/thread.jpg"},
        }
        (pack_dir / "threads.yml").write_text(yaml.safe_dump(threads, sort_keys=False), encoding="utf-8")
        (pack_dir / "threads.md").write_text("Threads caption", encoding="utf-8")
        (pack_dir / "publish_log.yml").write_text("events: []\n", encoding="utf-8")
        return pack_dir

    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = publish_threads_live.main(argv, self.content_dir, self.now, self.env)
        return code, out.getvalue(), err.getvalue()

    def test_dry_run_text(self) -> None:
        self.create_pack(post_type="text")
        code, out, err = self.run_main([])
        self.assertEqual(code, 0)
        self.assertIn("WOULD_PUBLISH pack=test-pack type=text", out)
        self.assertEqual(err, "")

    def test_live_publish_image(self) -> None:
        pack_dir = self.create_pack(post_type="image")
        create = Mock(status_code=200)
        create.json.return_value = {"id": "creation-1"}
        publish = Mock(status_code=200)
        publish.json.return_value = {"id": "thread-1"}
        with patch.object(publish_threads_live.requests, "post", side_effect=[create, publish]):
            code, out, err = self.run_main(["--live"])
        self.assertEqual(code, 0)
        self.assertIn("PUBLISHED test-pack: external_id=thread-1", out)
        self.assertEqual(err, "")
        saved = publish_threads_live.load_yaml(pack_dir / "threads.yml")
        self.assertEqual(saved["status"], "published")
        self.assertEqual(saved["external_id"], "thread-1")

    def test_live_pack_filter(self) -> None:
        self.create_pack(post_type="text")
        create = Mock(status_code=200)
        create.json.return_value = {"id": "creation-2"}
        publish = Mock(status_code=200)
        publish.json.return_value = {"id": "thread-2"}
        with patch.object(publish_threads_live.requests, "post", side_effect=[create, publish]) as post:
            code, out, _ = self.run_main(["--live", "--pack", "test-pack"])
        self.assertEqual(code, 0)
        self.assertIn("PUBLISHED test-pack", out)
        self.assertEqual(post.call_count, 2)

    def test_missing_token_fail_closed(self) -> None:
        self.create_pack(post_type="text")
        code = publish_threads_live.main(["--live"], self.content_dir, self.now, {"THREADS_USER_ID": "1"})
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

