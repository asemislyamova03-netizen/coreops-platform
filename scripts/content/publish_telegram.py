from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import requests
import yaml
from dateutil.parser import isoparse


ROOT = Path(__file__).resolve().parents[2]
CONTENT_PACKS_DIR = ROOT / "landing" / "content" / "content-packs"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


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


def should_publish(pack: dict[str, Any], now: datetime | None = None) -> tuple[bool, str]:
    if pack.get("status") != "approved":
        return False, "pack.status is not approved"

    publish = pack.get("publish")
    if not isinstance(publish, dict):
        return False, "publish is missing or invalid"

    telegram = publish.get("telegram")
    if not isinstance(telegram, dict):
        return False, "publish.telegram is missing or invalid"

    if telegram.get("enabled") is not True:
        return False, "publish.telegram.enabled is not true"
    if telegram.get("status") != "approved":
        return False, "publish.telegram.status is not approved"
    if telegram.get("published_at") is not None:
        return False, "already published"

    publish_at = telegram.get("publish_at")
    if not publish_at:
        return False, "publish.telegram.publish_at is missing"

    try:
        publish_dt = isoparse(str(publish_at))
    except (TypeError, ValueError, OverflowError):
        return False, "publish.telegram.publish_at is invalid"

    if publish_dt.tzinfo is None or publish_dt.utcoffset() is None:
        return False, "publish.telegram.publish_at must include a timezone"

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must include a timezone")
    if publish_dt > current:
        return False, "publish.telegram.publish_at is in the future"

    return True, "ready"


def send_telegram_message(token: str, chat_id: str, text: str) -> int:
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Telegram API request failed: {type(exc).__name__}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Telegram API returned invalid JSON (HTTP {response.status_code})"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Telegram API returned an invalid payload (HTTP {response.status_code})"
        )

    if response.status_code >= 400 or not payload.get("ok"):
        description = payload.get("description", "request failed")
        raise RuntimeError(
            f"Telegram API error (HTTP {response.status_code}): {description}"
        )

    result = payload.get("result")
    message_id = result.get("message_id") if isinstance(result, dict) else None
    if not isinstance(message_id, int):
        raise RuntimeError("Telegram API response has no integer message_id")
    return message_id


def main(
    content_packs_dir: Path = CONTENT_PACKS_DIR,
    environ: Mapping[str, str] | None = None,
) -> int:
    environment = environ if environ is not None else os.environ
    token = environment.get("TELEGRAM_BOT_TOKEN")
    chat_id = environment.get("TELEGRAM_CHAT_ID")

    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set", file=sys.stderr)
        return 1
    if not chat_id:
        print("ERROR: TELEGRAM_CHAT_ID is not set", file=sys.stderr)
        return 1

    if not content_packs_dir.exists():
        print(f"No content packs directory: {content_packs_dir}")
        return 0

    published_count = 0
    error_count = 0

    for pack_path in sorted(content_packs_dir.glob("*/pack.yml")):
        pack_dir = pack_path.parent
        try:
            pack = load_yaml(pack_path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            error_count += 1
            print(f"ERROR {pack_dir.name}: cannot read pack.yml: {exc}", file=sys.stderr)
            continue

        allowed, reason = should_publish(pack)
        if not allowed:
            print(f"SKIP {pack_dir.name}: {reason}")
            continue

        telegram_path = pack_dir / "telegram.md"
        try:
            text = telegram_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            text = ""
            reason = "telegram.md not found"
        except OSError as exc:
            error_count += 1
            print(f"ERROR {pack_dir.name}: cannot read telegram.md: {exc}", file=sys.stderr)
            continue
        else:
            reason = "telegram.md is empty"

        if not text:
            try:
                append_log(
                    pack_dir,
                    {
                        "at": now_iso(),
                        "channel": "telegram",
                        "status": "skipped",
                        "reason": reason,
                    },
                )
            except (OSError, ValueError, yaml.YAMLError) as exc:
                error_count += 1
                print(f"ERROR {pack_dir.name}: cannot write publish log: {exc}", file=sys.stderr)
                continue
            print(f"SKIP {pack_dir.name}: {reason}")
            continue

        try:
            message_id = send_telegram_message(token, chat_id, text)
            published_at = now_iso()
            telegram = pack["publish"]["telegram"]
            telegram["published_at"] = published_at
            telegram["external_id"] = message_id
            save_yaml(pack_path, pack)
            append_log(
                pack_dir,
                {
                    "at": published_at,
                    "channel": "telegram",
                    "status": "published",
                    "message_id": message_id,
                },
            )
        except (OSError, ValueError, RuntimeError, yaml.YAMLError) as exc:
            error_count += 1
            try:
                append_log(
                    pack_dir,
                    {
                        "at": now_iso(),
                        "channel": "telegram",
                        "status": "error",
                        "error": str(exc),
                    },
                )
            except (OSError, ValueError, yaml.YAMLError) as log_exc:
                print(
                    f"ERROR {pack_dir.name}: cannot write publish log: {log_exc}",
                    file=sys.stderr,
                )
            print(f"ERROR {pack_dir.name}: {exc}", file=sys.stderr)
            continue

        published_count += 1
        print(f"PUBLISHED {pack_dir.name}: message_id={message_id}")

    print(f"Done. Published: {published_count}. Errors: {error_count}")
    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
