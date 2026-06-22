from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

import yaml
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
CANVAS_SIZE = (1080, 1080)
CONTENT_PACKS_RELATIVE = Path("landing/content/content-packs")
SOCIAL_ASSETS_RELATIVE = Path("landing/www/assets/social")


class GenerationError(ValueError):
    pass


def is_within(path: Path, directory: Path) -> bool:
    return path == directory or path.is_relative_to(directory)


def resolve_pack(pack: str | Path, root: Path) -> Path:
    root = root.resolve()
    allowed = (root / CONTENT_PACKS_RELATIVE).resolve()
    candidate = Path(pack)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if not is_within(candidate, allowed):
        raise GenerationError("pack must be inside landing/content/content-packs/")
    if not candidate.is_dir():
        raise GenerationError(f"content pack directory not found: {candidate}")
    return candidate


def resolve_output(value: Any, root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise GenerationError("instagram_feed.output is required")

    root = root.resolve()
    allowed = (root / SOCIAL_ASSETS_RELATIVE).resolve()
    candidate = Path(value.strip())
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()

    if not is_within(candidate, allowed):
        raise GenerationError(
            "output must be inside landing/www/assets/social/"
        )
    if candidate.suffix.lower() != ".png":
        raise GenerationError("instagram-feed output must use the .png extension")
    return candidate


def load_visual(pack_dir: Path) -> dict[str, str]:
    visual_path = pack_dir / "visual.yml"
    if not visual_path.is_file():
        raise GenerationError(f"visual.yml not found in content pack: {pack_dir.name}")

    try:
        with visual_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise GenerationError(f"cannot read visual.yml: {exc}") from exc

    if not isinstance(data, dict):
        raise GenerationError("visual.yml must contain a YAML mapping")
    config = data.get("instagram_feed")
    if not isinstance(config, dict):
        raise GenerationError("visual.yml requires an instagram_feed mapping")

    normalized: dict[str, str] = {}
    for field in ("title", "subtitle", "footer"):
        value = config.get(field)
        if not isinstance(value, str) or not value.strip():
            raise GenerationError(f"instagram_feed.{field} is required")
        normalized[field] = value.strip()
    normalized["output"] = config.get("output")
    return normalized


def font_candidates(bold: bool) -> list[Path]:
    if bold:
        names = (
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        )
    else:
        names = (
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        )
    return [Path(name) for name in names]


def resolve_font(bold: bool) -> Path:
    for candidate in font_candidates(bold):
        if candidate.is_file():
            return candidate
    style = "bold" if bold else "regular"
    raise GenerationError(
        f"no local TrueType font found for {style} text; install Arial, Segoe UI, "
        "DejaVu Sans, or Liberation Sans"
    )


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def split_long_word(
    draw: ImageDraw.ImageDraw,
    word: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    parts: list[str] = []
    current = ""
    for character in word:
        candidate = current + character
        if current and text_width(draw, candidate, font) > max_width:
            parts.append(current)
            current = character
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    current = ""
    for paragraph_index, paragraph in enumerate(text.splitlines() or [text]):
        words: list[str] = []
        for word in paragraph.split():
            if text_width(draw, word, font) > max_width:
                words.extend(split_long_word(draw, word, font, max_width))
            else:
                words.append(word)

        for word in words:
            candidate = word if not current else f"{current} {word}"
            if current and text_width(draw, candidate, font) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
            current = ""
        if paragraph_index < len(text.splitlines()) - 1:
            lines.append("")
    return lines or [""]


def line_metrics(font: ImageFont.FreeTypeFont, spacing: int) -> tuple[int, int]:
    box = font.getbbox("Ag")
    line_height = box[3] - box[1]
    return line_height, line_height + spacing


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Path,
    max_width: int,
    max_height: int,
    max_size: int,
    min_size: int,
) -> tuple[ImageFont.FreeTypeFont, list[str], int, int]:
    for size in range(max_size, min_size - 1, -4):
        font = ImageFont.truetype(str(font_path), size=size)
        lines = wrap_text(draw, text, font, max_width)
        spacing = max(8, size // 5)
        line_height, step = line_metrics(font, spacing)
        height = line_height + step * (len(lines) - 1)
        if height <= max_height:
            return font, lines, spacing, height
    raise GenerationError("text is too long for the Instagram feed layout")


def draw_centered_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    color: tuple[int, int, int],
    top: int,
    spacing: int,
) -> None:
    line_height, step = line_metrics(font, spacing)
    y = top
    for line in lines:
        width = text_width(draw, line, font)
        draw.text(((CANVAS_SIZE[0] - width) // 2, y), line, font=font, fill=color)
        y += step


def render_instagram_feed(config: dict[str, str], output_path: Path) -> None:
    bold_font_path = resolve_font(bold=True)
    regular_font_path = resolve_font(bold=False)

    image = Image.new("RGB", CANVAS_SIZE, color=(247, 248, 244))
    draw = ImageDraw.Draw(image)
    dark = (24, 31, 35)
    muted = (76, 88, 92)
    accent = (26, 126, 104)

    draw.rounded_rectangle((86, 78, 994, 92), radius=7, fill=accent)
    brand_font = ImageFont.truetype(str(bold_font_path), size=28)
    brand = "FLEXITY"
    brand_width = text_width(draw, brand, brand_font)
    draw.text(((1080 - brand_width) // 2, 128), brand, font=brand_font, fill=accent)

    title_font, title_lines, title_spacing, title_height = fit_text(
        draw,
        config["title"],
        bold_font_path,
        max_width=888,
        max_height=350,
        max_size=96,
        min_size=56,
    )
    title_top = 250 + (350 - title_height) // 2
    draw_centered_lines(
        draw, title_lines, title_font, dark, title_top, title_spacing
    )

    subtitle_font, subtitle_lines, subtitle_spacing, subtitle_height = fit_text(
        draw,
        config["subtitle"],
        regular_font_path,
        max_width=820,
        max_height=150,
        max_size=52,
        min_size=34,
    )
    subtitle_top = 650 + (150 - subtitle_height) // 2
    draw_centered_lines(
        draw, subtitle_lines, subtitle_font, muted, subtitle_top, subtitle_spacing
    )

    draw.line((146, 876, 934, 876), fill=(205, 213, 209), width=2)
    footer_font, footer_lines, footer_spacing, footer_height = fit_text(
        draw,
        config["footer"],
        regular_font_path,
        max_width=820,
        max_height=96,
        max_size=32,
        min_size=24,
    )
    footer_top = 920 + (96 - footer_height) // 2
    draw_centered_lines(
        draw, footer_lines, footer_font, muted, footer_top, footer_spacing
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output_path.stem}.", suffix=".tmp", dir=output_path.parent
        )
        os.close(file_descriptor)
        temporary_path = Path(temporary_name)
        image.save(temporary_path, format="PNG", optimize=True)
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def generate_asset(
    pack: str | Path,
    asset_type: str,
    root: Path = ROOT,
) -> Path:
    if asset_type != "instagram-feed":
        raise GenerationError("only --type instagram-feed is supported")
    pack_dir = resolve_pack(pack, root)
    config = load_visual(pack_dir)
    output_path = resolve_output(config.get("output"), root)
    render_instagram_feed(config, output_path)
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate local social media assets from a Flexity content pack."
    )
    parser.add_argument("--pack", required=True, help="Path to the content-pack directory.")
    parser.add_argument(
        "--type",
        required=True,
        choices=("instagram-feed",),
        help="Asset type to generate.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output_path = generate_asset(args.pack, args.type)
    except (GenerationError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"GENERATED {output_path} size=1080x1080")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
