"""Timezone conversion for Booking — local territory time to UTC instants."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.modules.booking.exceptions import BookingTimezoneError
from app.modules.booking.models import BookingBookableObject, BookingTerritory
from app.modules.booking.schemas import ResolvedStayInterval


def utc_now() -> datetime:
    return datetime.now(UTC)


def is_valid_timezone(tz_name: str) -> bool:
    try:
        ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return False
    return True


def resolve_effective_check_times(
    territory: BookingTerritory,
    bookable_object: BookingBookableObject,
) -> tuple[time, time]:
    check_in = bookable_object.check_in_time or territory.default_check_in_time
    check_out = bookable_object.check_out_time or territory.default_check_out_time
    return check_in, check_out


def local_stay_to_utc_instant(local_day: date, local_clock: time, tz_name: str) -> datetime:
    if not is_valid_timezone(tz_name):
        raise BookingTimezoneError(f"Unknown timezone: {tz_name}")

    tz = ZoneInfo(tz_name)
    try:
        local_dt = datetime.combine(local_day, local_clock, tzinfo=tz)
    except Exception as exc:
        raise BookingTimezoneError(
            f"Cannot resolve local datetime {local_day} {local_clock} in {tz_name}"
        ) from exc

    return local_dt.astimezone(UTC)


def build_item_interval(
    territory: BookingTerritory,
    bookable_object: BookingBookableObject,
    check_in_date: date,
    check_out_date: date,
) -> ResolvedStayInterval:
    if check_out_date <= check_in_date:
        raise BookingTimezoneError("check_out_date must be after check_in_date")

    check_in_time, check_out_time = resolve_effective_check_times(territory, bookable_object)
    check_in_at = local_stay_to_utc_instant(check_in_date, check_in_time, territory.timezone)
    check_out_at = local_stay_to_utc_instant(check_out_date, check_out_time, territory.timezone)

    if check_out_at <= check_in_at:
        raise BookingTimezoneError("check_out_at must be after check_in_at in UTC")

    nights = (check_out_date - check_in_date).days
    if nights < 1:
        nights = 1

    return ResolvedStayInterval(
        bookable_object_id=bookable_object.id,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        check_in_at=check_in_at,
        check_out_at=check_out_at,
        nights=nights,
    )


def intervals_overlap(
    left_check_in: datetime,
    left_check_out: datetime,
    right_check_in: datetime,
    right_check_out: datetime,
) -> bool:
    """Half-open interval overlap: [check_in, check_out)."""
    return left_check_in < right_check_out and left_check_out > right_check_in
