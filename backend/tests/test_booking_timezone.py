"""E2a timezone conversion tests for Flexity Booking."""

from datetime import UTC, date, datetime, time

import pytest

from app.modules.booking.exceptions import BookingTimezoneError
from app.modules.booking.service.timezone import (
    build_item_interval,
    intervals_overlap,
    is_valid_timezone,
    local_stay_to_utc_instant,
    resolve_effective_check_times,
)
from tests.test_booking_models import _bootstrap_booking_graph


def test_is_valid_timezone():
    assert is_valid_timezone("Asia/Almaty")
    assert is_valid_timezone("UTC")
    assert not is_valid_timezone("Not/A_Real_Zone")


def test_local_stay_to_utc_instant_asia_almaty():
    instant = local_stay_to_utc_instant(date(2026, 7, 10), time(14, 0), "Asia/Almaty")
    assert instant.tzinfo == UTC
    # Almaty is UTC+5 in July (no DST)
    assert instant == datetime(2026, 7, 10, 9, 0, tzinfo=UTC)


def test_local_stay_to_utc_unknown_timezone():
    with pytest.raises(BookingTimezoneError):
        local_stay_to_utc_instant(date(2026, 7, 10), time(14, 0), "Invalid/Zone")


def test_resolve_effective_check_times_object_override(db_session):
    _tenant, territory, _owner, obj, _guest = _bootstrap_booking_graph(db_session)

    check_in, check_out = resolve_effective_check_times(territory, obj)
    assert check_in == time(15, 0)
    assert check_out == time(11, 0)


def test_build_item_interval_uses_territory_timezone(db_session):
    _tenant, territory, _owner, obj, _guest = _bootstrap_booking_graph(db_session)

    interval = build_item_interval(territory, obj, date(2026, 8, 1), date(2026, 8, 3))

    assert interval.check_in_at == datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
    assert interval.check_out_at == datetime(2026, 8, 3, 6, 0, tzinfo=UTC)
    assert interval.nights == 2


def test_build_item_interval_rejects_invalid_dates(db_session):
    _tenant, territory, _owner, obj, _guest = _bootstrap_booking_graph(db_session)

    with pytest.raises(BookingTimezoneError):
        build_item_interval(territory, obj, date(2026, 8, 3), date(2026, 8, 1))


def test_intervals_overlap_half_open():
    left_in = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
    left_out = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
    touch_in = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
    touch_out = datetime(2026, 8, 5, 9, 0, tzinfo=UTC)

    assert intervals_overlap(left_in, left_out, touch_in, touch_out) is False
    assert intervals_overlap(left_in, left_out, left_in, left_out) is True
