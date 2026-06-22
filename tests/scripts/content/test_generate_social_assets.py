from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml
from PIL import Image


SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "content"
    / "generate_social_assets.py"
)
SPEC = importlib.util.spec_from_file_location("generate_social_assets", SCRIPT_PATH)
assert SPEC and SPEC.loader
generate_social_assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_social_assets)


class SocialAssetGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.pack_relative = Path(
            "landing/content/content-packs/2026-06-23-process-before-ai"
        )
        self.pack_dir = self.root / self.pack_relative
        self.pack_dir.mkdir(parents=True)
        self.output_relative = Path(
            "landing/www/assets/social/2026-06-23-process-before-ai/instagram-feed.png"
        )

    def write_visual(self, *, output: str | None = None) -> bytes:
        instagram_feed = {
            "title": "AI не спасёт бизнес",
            "subtitle": "если процесс в хаосе",
            "footer": "Flexity • сначала процесс, потом AI",
        }
        if output is not None:
            instagram_feed["output"] = output
        data = {"instagram_feed": instagram_feed}
        visual_path = self.pack_dir / "visual.yml"
        visual_path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return visual_path.read_bytes()

    def test_valid_config_creates_1080_square_png(self) -> None:
        visual_before = self.write_visual(output=self.output_relative.as_posix())

        output = generate_social_assets.generate_asset(
            self.pack_relative, "instagram-feed", self.root
        )

        self.assertEqual(output, (self.root / self.output_relative).resolve())
        self.assertTrue(output.is_file())
        with Image.open(output) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.size, (1080, 1080))
            colors = image.getcolors(maxcolors=1080 * 1080)
            self.assertIsNotNone(colors)
            self.assertGreater(len(colors), 3)
        self.assertEqual((self.pack_dir / "visual.yml").read_bytes(), visual_before)

    def test_missing_visual_yml_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            generate_social_assets.GenerationError, "visual.yml not found"
        ):
            generate_social_assets.generate_asset(
                self.pack_relative, "instagram-feed", self.root
            )
        self.assertFalse((self.root / self.output_relative).exists())

    def test_missing_output_fails_closed(self) -> None:
        self.write_visual()

        with self.assertRaisesRegex(
            generate_social_assets.GenerationError,
            "instagram_feed.output is required",
        ):
            generate_social_assets.generate_asset(
                self.pack_relative, "instagram-feed", self.root
            )
        self.assertFalse((self.root / self.output_relative).exists())

    def test_output_outside_social_assets_fails_closed(self) -> None:
        unsafe_relative = Path("landing/www/assets/escape.png")
        self.write_visual(output=unsafe_relative.as_posix())

        with self.assertRaisesRegex(
            generate_social_assets.GenerationError,
            "output must be inside landing/www/assets/social/",
        ):
            generate_social_assets.generate_asset(
                self.pack_relative, "instagram-feed", self.root
            )
        self.assertFalse((self.root / unsafe_relative).exists())

    def test_path_traversal_outside_social_assets_fails_closed(self) -> None:
        traversal = (
            "landing/www/assets/social/2026-06-23-process-before-ai/../../escape.png"
        )
        self.write_visual(output=traversal)

        with self.assertRaisesRegex(
            generate_social_assets.GenerationError,
            "output must be inside landing/www/assets/social/",
        ):
            generate_social_assets.generate_asset(
                self.pack_relative, "instagram-feed", self.root
            )
        self.assertFalse((self.root / "landing/www/assets/escape.png").exists())

    def test_non_png_output_fails_closed(self) -> None:
        invalid_output = Path(
            "landing/www/assets/social/2026-06-23-process-before-ai/feed.jpg"
        )
        self.write_visual(output=invalid_output.as_posix())

        with self.assertRaisesRegex(
            generate_social_assets.GenerationError, "must use the .png extension"
        ):
            generate_social_assets.generate_asset(
                self.pack_relative, "instagram-feed", self.root
            )
        self.assertFalse((self.root / invalid_output).exists())

    def test_unsupported_type_fails_closed(self) -> None:
        self.write_visual(output=self.output_relative.as_posix())

        with self.assertRaisesRegex(
            generate_social_assets.GenerationError,
            "only --type instagram-feed is supported",
        ):
            generate_social_assets.generate_asset(
                self.pack_relative, "reels", self.root
            )
        self.assertFalse((self.root / self.output_relative).exists())


if __name__ == "__main__":
    unittest.main()
