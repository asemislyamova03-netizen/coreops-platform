"""Party contact matching helpers (normalize + compare). No DB writes."""

from __future__ import annotations

import re

MIN_PHONE_DIGITS = 10

EXACT_MATCH_KEYS = (
    "telegram_user_id",
    "email",
    "phone",
    "whatsapp",
    "telegram_username",
)

EXACT_KEY_SCORE = {
    "telegram_user_id": 100,
    "email": 95,
    "phone": 90,
    "whatsapp": 90,
    "telegram_username": 85,
}

WEAK_NAME_SCORE = 30


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def normalize_phone_digits(value: str | None) -> str | None:
    """Normalize phone/whatsapp to digits-only national form.

    Conservative rules:
    - strip non-digits;
    - 8XXXXXXXXXX (11 digits, RU/KZ style) → 7XXXXXXXXXX;
    - reject if fewer than MIN_PHONE_DIGITS digits (avoid short-number overmatch).
    """
    if value is None:
        return None
    digits = re.sub(r"\D+", "", value.strip())
    if not digits:
        return None
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) < MIN_PHONE_DIGITS:
        return None
    return digits


def normalize_telegram_username(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized.startswith("@"):
        normalized = normalized[1:]
    return normalized or None


def normalize_telegram_user_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def phones_match(left: str | None, right: str | None) -> bool:
    a = normalize_phone_digits(left)
    b = normalize_phone_digits(right)
    return bool(a and b and a == b)


def emails_match(left: str | None, right: str | None) -> bool:
    a = normalize_email(left)
    b = normalize_email(right)
    return bool(a and b and a == b)


def telegram_usernames_match(left: str | None, right: str | None) -> bool:
    a = normalize_telegram_username(left)
    b = normalize_telegram_username(right)
    return bool(a and b and a == b)


def looks_like_telegram_user_id(value: str | None) -> bool:
    """Conservative: Telegram user ids are numeric strings."""
    normalized = normalize_telegram_user_id(value)
    return bool(normalized and normalized.isdigit())


def telegram_user_ids_match(left: str | None, right: str | None) -> bool:
    a = normalize_telegram_user_id(left)
    b = normalize_telegram_user_id(right)
    if not (a and b and a == b):
        return False
    # Avoid treating usernames as user_id matches.
    return looks_like_telegram_user_id(a) and looks_like_telegram_user_id(b)


def score_for_matched_on(matched_on: list[str], *, match_type: str) -> int:
    if match_type == "weak":
        return WEAK_NAME_SCORE
    if not matched_on:
        return 0
    return max(EXACT_KEY_SCORE.get(key, 50) for key in matched_on)


def telegram_user_id_from_metadata(metadata: dict | None) -> str | None:
    if not metadata:
        return None
    telegram = metadata.get("telegram")
    if isinstance(telegram, dict):
        raw = telegram.get("user_id")
        if raw is not None:
            return normalize_telegram_user_id(str(raw))
    raw_top = metadata.get("telegram_user_id")
    if raw_top is not None:
        return normalize_telegram_user_id(str(raw_top))
    return None
