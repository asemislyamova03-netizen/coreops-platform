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
TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"
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
            yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False, default_flow_style=False)
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


def should_publish(pack: dict[str, Any], config: dict[str, Any], now: datetime) -> tuple[bool, str, datetime | None]:
    if pack.get("status") != "approved":
        return False, "pack.status is not approved", None
    if config.get("status") != "approved":
        return False, "status is not approved", None
    if config.get("published_at") is not None or config.get("external_id") is not None:
        return False, "already published", None
    publish_at = parse_publish_at(config.get("publish_at"))
    if publish_at > now:
        return False, "publish_at is in the future", publish_at
    return True, "ready", publish_at


def validate_tiktok(pack_dir: Path, config: dict[str, Any]) -> tuple[str, str]:
    post_type = str(config.get("type") or "video").strip().lower()
    if post_type != "video":
        raise ValueError("type must be video")
    media = config.get("media")
    if not isinstance(media, dict):
        raise ValueError("media must be a YAML mapping")
    video_url = str(media.get("video_url") or "").strip()
    if not video_url:
        raise ValueError("media.video_url is required")
    if not video_url.startswith("https://"):
        raise ValueError("media.video_url must start with https://")
    _ = read_caption(pack_dir, config)
    return post_type, video_url


def check_secrets(environment: Mapping[str, str]) -> str | None:
    if not environment.get("TIKTOK_ACCESS_TOKEN"):
        return "TIKTOK_ACCESS_TOKEN"
    return None


def parse_response(response: requests.Response, step: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"TikTok API invalid JSON during {step} (HTTP {response.status_code})") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"TikTok API invalid payload during {step} (HTTP {response.status_code})")
    if response.status_code >= 400 or payload.get("error"):
        message = "request failed"
        error = payload.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or message)
        raise RuntimeError(f"TikTok API error during {step} (HTTP {response.status_code}): {message}")
    return payload


def publish_one(pack_dir: Path, config: dict[str, Any], token: str) -> str:
    _, video_url = validate_tiktok(pack_dir, config)
    caption = read_caption(pack_dir, config)
    try:
        response = requests.post(
            f"{TIKTOK_API_BASE}/post/publish/video/init/",
            json={"post_info": {"title": caption[:150]}, "source_info": {"source": "PULL_FROM_URL", "video_url": video_url}},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"TikTok API request failed: {type(exc).__name__}") from exc
    body = parse_response(response, "publish")
    external_id = str((body.get("data") or {}).get("publish_id") or "")
    if not external_id:
        raise RuntimeError("TikTok API response has no publish_id")
    published_at = now_iso()
    config["published_at"] = published_at
    config["external_id"] = external_id
    config["status"] = "published"
    save_yaml(pack_dir / "tiktok.yml", config)
    append_log(pack_dir, {"at": published_at, "channel": "tiktok", "status": "published", "external_id": external_id})
    return external_id


def run_scan(*, content_packs_dir: Path, now: datetime, live: bool, environment: Mapping[str, str], pack_filter: str | None) -> int:
    if live:
        missing = check_secrets(environment)
        if missing:
            print(f"ERROR: {missing} is not set", file=sys.stderr)
            return 1
    if not content_packs_dir.exists():
        print(f"No content packs directory: {content_packs_dir}")
        return 0
    token = environment.get("TIKTOK_ACCESS_TOKEN", "")
    matched = 0
    done = 0
    errors = 0
    for config_path in sorted(content_packs_dir.glob("*/tiktok.yml")):
        pack_dir = config_path.parent
        if pack_filter and pack_dir.name != pack_filter:
            continue
        matched += 1
        try:
            pack = load_yaml(pack_dir / "pack.yml")
            config = load_yaml(config_path)
            allowed, reason, publish_at = should_publish(pack, config, now)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors += 1
            print(f"ERROR {pack_dir.name}: {exc}", file=sys.stderr)
            continue
        if not allowed:
            print(f"SKIP {pack_dir.name}: {reason}")
            continue
        try:
            _, video_url = validate_tiktok(pack_dir, config)
        except (OSError, ValueError, UnicodeError) as exc:
            errors += 1
            print(f"ERROR {pack_dir.name}: {exc}", file=sys.stderr)
            continue
        if not live:
            print(
                f"WOULD_PUBLISH pack={pack_dir.name} type=video "
                f"video_url={video_url} publish_at={publish_at.isoformat()} would_publish=true"
            )
            done += 1
            continue
        try:
            external_id = publish_one(pack_dir, config, token)
        except (OSError, ValueError, RuntimeError, yaml.YAMLError) as exc:
            errors += 1
            safe = sanitize_error(str(exc))
            try:
                append_log(pack_dir, {"at": now_iso(), "channel": "tiktok", "status": "error", "error": safe})
            except Exception:
                pass
            print(f"ERROR {pack_dir.name}: {safe}", file=sys.stderr)
            continue
        done += 1
        print(f"PUBLISHED {pack_dir.name}: external_id={external_id}")
    if pack_filter and matched == 0:
        print(f"SKIP {pack_filter}: tiktok.yml not found")
    print(f"Done. {'Published' if live else 'Would publish'}: {done}. Errors: {errors}")
    return 1 if errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish TikTok content packs.")
    parser.add_argument("--live", action="store_true", help="Publish eligible packs via TikTok API.")
    parser.add_argument("--pack", type=str, default="", help="Optional single pack_dir name.")
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
    pack_filter = args.pack.strip() or None
    return run_scan(
        content_packs_dir=content_packs_dir,
        now=current,
        live=args.live,
        environment=environment,
        pack_filter=pack_filter,
    )


if __name__ == "__main__":
    raise SystemExit(main())
