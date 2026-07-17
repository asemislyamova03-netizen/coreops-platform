from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import requests
import yaml

from publish_instagram import load_yaml, parse_publish_at, read_caption


ROOT = Path(__file__).resolve().parents[2]
CONTENT_PACKS_DIR = ROOT / "landing" / "content" / "content-packs"
GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
SUPPORTED_TYPES = {"feed_image", "carousel", "reels"}
MVP_CAPTION_SOURCE = "instagram.md"
TOKEN_REDACT_PATTERN = re.compile(r"access_token=[^&\s]+", re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            yaml.safe_dump(
                data,
                file,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
            temporary_path = Path(file.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def append_log(pack_dir: Path, event: dict[str, Any]) -> None:
    log_path = pack_dir / "publish_log.yml"
    log_data = load_yaml(log_path) if log_path.exists() else {}
    events = log_data.get("events", [])
    if not isinstance(events, list):
        raise ValueError(f"{log_path}: events must be a list")
    events.append(event)
    log_data["events"] = events
    save_yaml(log_path, log_data)


def sanitize_error(message: str) -> str:
    return TOKEN_REDACT_PATTERN.sub("access_token=[REDACTED]", message)


def pack_eligibility(pack: dict[str, Any]) -> tuple[bool, str]:
    if pack.get("status") != "approved":
        return False, "pack.status is not approved"
    return True, "ready"


def instagram_eligibility(
    config: dict[str, Any], now: datetime
) -> tuple[bool, str, datetime | None]:
    if config.get("status") != "approved":
        return False, "status is not approved", None
    if config.get("published_at") is not None:
        return False, "already published", None
    if config.get("external_id") is not None:
        return False, "already published", None

    publish_at = parse_publish_at(config.get("publish_at"))
    if publish_at > now:
        return False, "publish_at is in the future", publish_at
    return True, "ready", publish_at


def should_publish(
    pack: dict[str, Any], config: dict[str, Any], now: datetime
) -> tuple[bool, str, datetime | None]:
    allowed, reason = pack_eligibility(pack)
    if not allowed:
        return False, reason, None
    return instagram_eligibility(config, now)


def _validate_caption_source(pack_dir: Path, config: dict[str, Any]) -> str:
    media = config.get("media")
    if not isinstance(media, dict):
        raise ValueError("media must be a YAML mapping")

    source = config.get("caption_source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("caption_source is required")
    if source.strip() != MVP_CAPTION_SOURCE:
        raise ValueError(f"caption_source must be {MVP_CAPTION_SOURCE} for live publisher MVP")

    return read_caption(pack_dir, config)


def _validate_https_url(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    normalized = value.strip()
    if not normalized.startswith("https://"):
        raise ValueError(f"{field} must start with https://")
    return normalized


def validate_instagram_media_mvp(
    pack_dir: Path, config: dict[str, Any]
) -> tuple[str, str, list[dict[str, str]]]:
    post_type = str(config.get("type") or "").strip()
    if post_type not in SUPPORTED_TYPES:
        raise ValueError(f"type must be one of {sorted(SUPPORTED_TYPES)}")

    media = config.get("media")
    if not isinstance(media, dict):
        raise ValueError("media must be a YAML mapping")
    caption = _validate_caption_source(pack_dir, config)

    if post_type == "feed_image":
        image_url = _validate_https_url(media.get("image_url"), "media.image_url")
        return post_type, caption, [{"image_url": image_url}]

    if post_type == "reels":
        video_url = _validate_https_url(media.get("video_url"), "media.video_url")
        return post_type, caption, [{"video_url": video_url}]

    items = media.get("items")
    if not isinstance(items, list) or len(items) < 2:
        raise ValueError("media.items must be a non-empty list with at least 2 items for carousel")
    normalized_items: list[dict[str, str]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"media.items[{idx}] must be a mapping")
        if item.get("image_url"):
            normalized_items.append(
                {
                    "image_url": _validate_https_url(
                        item.get("image_url"), f"media.items[{idx}].image_url"
                    )
                }
            )
        elif item.get("video_url"):
            normalized_items.append(
                {
                    "video_url": _validate_https_url(
                        item.get("video_url"), f"media.items[{idx}].video_url"
                    )
                }
            )
        else:
            raise ValueError(f"media.items[{idx}] requires image_url or video_url")
    return post_type, caption, normalized_items


def check_secrets(environment: Mapping[str, str]) -> str | None:
    if not environment.get("INSTAGRAM_USER_ID"):
        return "INSTAGRAM_USER_ID"
    if not environment.get("INSTAGRAM_ACCESS_TOKEN"):
        return "INSTAGRAM_ACCESS_TOKEN"
    return None


def parse_graph_response(response: requests.Response, step: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Instagram API returned invalid JSON during {step} "
            f"(HTTP {response.status_code})"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Instagram API returned an invalid payload during {step} "
            f"(HTTP {response.status_code})"
        )

    if response.status_code >= 400 or payload.get("error"):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message", "request failed")
            code = error.get("code")
            if code is not None:
                description = f"{message} (code {code})"
            else:
                description = str(message)
        else:
            description = "request failed"
        raise RuntimeError(
            f"Instagram API error during {step} "
            f"(HTTP {response.status_code}): {description}"
        )
    return payload


def create_media_container(
    user_id: str, token: str, payload: dict[str, Any]
) -> str:
    try:
        response = requests.post(
            f"{GRAPH_API_BASE}/{user_id}/media",
            data={**payload, "access_token": token},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Instagram API request failed during media container creation: "
            f"{type(exc).__name__}"
        ) from exc

    payload = parse_graph_response(response, "media container creation")
    creation_id = payload.get("id")
    if not isinstance(creation_id, str) or not creation_id:
        raise RuntimeError(
            "Instagram API response has no creation id during media container creation"
        )
    return creation_id


def publish_media_container(user_id: str, token: str, creation_id: str) -> str:
    try:
        response = requests.post(
            f"{GRAPH_API_BASE}/{user_id}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": token,
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Instagram API request failed during media publish: "
            f"{type(exc).__name__}"
        ) from exc

    payload = parse_graph_response(response, "media publish")
    external_id = payload.get("id")
    if not isinstance(external_id, str) or not external_id:
        raise RuntimeError(
            "Instagram API response has no media id during media publish"
        )
    return external_id


def publish_pack(
    pack_dir: Path,
    config: dict[str, Any],
    post_type: str,
    media_items: list[dict[str, str]],
    caption: str,
    user_id: str,
    token: str,
) -> str:
    if post_type == "feed_image":
        creation_id = create_media_container(
            user_id, token, {"image_url": media_items[0]["image_url"], "caption": caption}
        )
    elif post_type == "reels":
        creation_id = create_media_container(
            user_id,
            token,
            {
                "media_type": "REELS",
                "video_url": media_items[0]["video_url"],
                "caption": caption,
            },
        )
    else:
        child_ids: list[str] = []
        for item in media_items:
            child_payload: dict[str, Any] = {"is_carousel_item": "true"}
            if "image_url" in item:
                child_payload["image_url"] = item["image_url"]
            else:
                child_payload["video_url"] = item["video_url"]
                child_payload["media_type"] = "VIDEO"
            child_ids.append(create_media_container(user_id, token, child_payload))
        creation_id = create_media_container(
            user_id,
            token,
            {
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
            },
        )
    external_id = publish_media_container(user_id, token, creation_id)

    published_at = now_iso()
    config["published_at"] = published_at
    config["external_id"] = external_id
    config["status"] = "published"
    save_yaml(pack_dir / "instagram.yml", config)
    append_log(
        pack_dir,
        {
            "at": published_at,
            "channel": "instagram",
            "status": "published",
            "external_id": external_id,
        },
    )
    return external_id


def run_scan(
    *,
    content_packs_dir: Path,
    now: datetime,
    live: bool,
    environment: Mapping[str, str],
) -> int:
    if live:
        missing = check_secrets(environment)
        if missing:
            print(f"ERROR: {missing} is not set", file=sys.stderr)
            return 1

    if not content_packs_dir.exists():
        print(f"No content packs directory: {content_packs_dir}")
        return 0

    user_id = environment.get("INSTAGRAM_USER_ID", "")
    token = environment.get("INSTAGRAM_ACCESS_TOKEN", "")

    preview_count = 0
    published_count = 0
    error_count = 0

    for config_path in sorted(content_packs_dir.glob("*/instagram.yml")):
        pack_dir = config_path.parent
        pack_path = pack_dir / "pack.yml"

        try:
            pack = load_yaml(pack_path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            error_count += 1
            print(
                f"ERROR {pack_dir.name}: cannot read pack.yml: {exc}",
                file=sys.stderr,
            )
            continue

        try:
            config = load_yaml(config_path)
            allowed, reason, publish_at = should_publish(pack, config, now)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            error_count += 1
            print(f"ERROR {pack_dir.name}: {exc}", file=sys.stderr)
            continue

        if not allowed:
            print(f"SKIP {pack_dir.name}: {reason}")
            continue

        try:
            post_type, caption, media_items = validate_instagram_media_mvp(pack_dir, config)
        except (OSError, UnicodeError, ValueError) as exc:
            error_count += 1
            print(f"ERROR {pack_dir.name}: {exc}", file=sys.stderr)
            continue

        if not live:
            media_preview: str
            if post_type == "carousel":
                media_preview = ",".join(
                    item.get("image_url") or item.get("video_url") or ""
                    for item in media_items
                )
            elif post_type == "reels":
                media_preview = media_items[0]["video_url"]
            else:
                media_preview = media_items[0]["image_url"]
            print(
                f"WOULD_PUBLISH pack={pack_dir.name} "
                f"type={post_type} "
                f"caption_length={len(caption)} "
                f"media_url={media_preview} "
                f"publish_at={publish_at.isoformat()} "
                "would_publish=true"
            )
            preview_count += 1
            continue

        try:
            external_id = publish_pack(
                pack_dir, config, post_type, media_items, caption, user_id, token
            )
        except (OSError, ValueError, RuntimeError, yaml.YAMLError) as exc:
            error_count += 1
            safe_error = sanitize_error(str(exc))
            try:
                append_log(
                    pack_dir,
                    {
                        "at": now_iso(),
                        "channel": "instagram",
                        "status": "error",
                        "error": safe_error,
                    },
                )
            except (OSError, ValueError, yaml.YAMLError) as log_exc:
                print(
                    f"ERROR {pack_dir.name}: cannot write publish log: {log_exc}",
                    file=sys.stderr,
                )
            print(f"ERROR {pack_dir.name}: {safe_error}", file=sys.stderr)
            continue

        published_count += 1
        print(f"PUBLISHED {pack_dir.name}: external_id={external_id}")

    if live:
        print(f"Done. Published: {published_count}. Errors: {error_count}")
    else:
        print(f"Done. Would publish: {preview_count}. Errors: {error_count}")
    return 1 if error_count else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publish approved Instagram feed_image/carousel/reels content packs."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Publish eligible packs via Meta API. Default is dry-run.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    content_packs_dir: Path = CONTENT_PACKS_DIR,
    now: datetime | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must include a timezone")

    environment = environ if environ is not None else os.environ
    return run_scan(
        content_packs_dir=content_packs_dir,
        now=current,
        live=args.live,
        environment=environment,
    )


if __name__ == "__main__":
    raise SystemExit(main())
