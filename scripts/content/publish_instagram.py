from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONTENT_PACKS_DIR = ROOT / "landing" / "content" / "content-packs"
SUPPORTED_TYPES = {"feed_image", "carousel", "reels"}
LIVE_NOT_IMPLEMENTED = (
    "Instagram live publishing is not implemented yet. Use --dry-run."
)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a YAML mapping")
    return data


def parse_publish_at(value: Any) -> datetime:
    if not value:
        raise ValueError("publish_at is missing")
    try:
        publish_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("publish_at is invalid") from exc
    if publish_at.tzinfo is None or publish_at.utcoffset() is None:
        raise ValueError("publish_at must include a timezone")
    return publish_at


def eligibility(
    config: dict[str, Any], now: datetime
) -> tuple[bool, str, datetime | None]:
    if config.get("status") != "approved":
        return False, "status is not approved", None
    if config.get("published_at") is not None:
        return False, "already published", None

    publish_at = parse_publish_at(config.get("publish_at"))
    if publish_at > now:
        return False, "publish_at is in the future", publish_at
    return True, "ready", publish_at


def public_url(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    normalized = value.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field} must be a public HTTP(S) URL")
    return normalized


def media_urls(config: dict[str, Any]) -> list[str]:
    post_type = config.get("type")
    if post_type not in SUPPORTED_TYPES:
        raise ValueError(
            "type must be one of: feed_image, carousel, reels"
        )

    media = config.get("media")
    if not isinstance(media, dict):
        raise ValueError("media must be a YAML mapping")

    if post_type == "feed_image":
        return [public_url(media.get("image_url"), "media.image_url")]
    if post_type == "reels":
        return [public_url(media.get("video_url"), "media.video_url")]

    items = media.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("media.items must be a non-empty list for carousel")

    urls: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"media.items[{index}] must be a YAML mapping")
        if item.get("image_url"):
            urls.append(
                public_url(item["image_url"], f"media.items[{index}].image_url")
            )
        elif item.get("video_url"):
            urls.append(
                public_url(item["video_url"], f"media.items[{index}].video_url")
            )
        else:
            raise ValueError(
                f"media.items[{index}] requires image_url or video_url"
            )
    return urls


def read_caption(pack_dir: Path, config: dict[str, Any]) -> str:
    source = config.get("caption_source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("caption_source is required")

    pack_root = pack_dir.resolve()
    caption_path = (pack_dir / source).resolve()
    if not caption_path.is_relative_to(pack_root):
        raise ValueError("caption_source must stay inside the content pack")
    if not caption_path.is_file():
        raise ValueError(f"caption source not found: {source}")

    caption = caption_path.read_text(encoding="utf-8").strip()
    if not caption:
        raise ValueError("caption source is empty")
    return caption


def run_dry_run(
    content_packs_dir: Path = CONTENT_PACKS_DIR,
    now: datetime | None = None,
) -> int:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must include a timezone")

    if not content_packs_dir.exists():
        print(f"No content packs directory: {content_packs_dir}")
        return 0

    preview_count = 0
    error_count = 0

    for config_path in sorted(content_packs_dir.glob("*/instagram.yml")):
        pack_dir = config_path.parent
        try:
            config = load_yaml(config_path)
            allowed, reason, publish_at = eligibility(config, current)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            error_count += 1
            print(f"ERROR {pack_dir.name}: {exc}", file=sys.stderr)
            continue

        if not allowed:
            print(f"SKIP {pack_dir.name}: {reason}")
            continue

        try:
            caption = read_caption(pack_dir, config)
            urls = media_urls(config)
        except (OSError, UnicodeError, ValueError) as exc:
            error_count += 1
            print(f"ERROR {pack_dir.name}: {exc}", file=sys.stderr)
            continue

        media_value = ",".join(urls)
        print(
            f"WOULD_PUBLISH pack={pack_dir.name} "
            f"type={config['type']} "
            f"caption_length={len(caption)} "
            f"media_url={media_value} "
            f"publish_at={publish_at.isoformat()} "
            "would_publish=true"
        )
        preview_count += 1

    print(f"Done. Would publish: {preview_count}. Errors: {error_count}")
    return 1 if error_count else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Instagram content packs without publishing."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and preview eligible packs without side effects.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    content_packs_dir: Path = CONTENT_PACKS_DIR,
    now: datetime | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    if not args.dry_run:
        print(LIVE_NOT_IMPLEMENTED, file=sys.stderr)
        return 2
    return run_dry_run(content_packs_dir, now)


if __name__ == "__main__":
    raise SystemExit(main())
