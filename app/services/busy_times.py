"""Busy-time lookup for availability and booking creation.

ScheduleLink stores ``Booking.start_time`` as **naive host-local wall-clock
time** (see the comment in ``schemas/booking.py``). Availability rules are also
naive local. Google and Microsoft, by contrast, return busy periods as naive
UTC. Everything this module returns is converted into the SAME naive-local
basis so callers can compare it directly against rule-generated slots.

Before this module existed, ``list_busy`` was defined in both calendar services
but never called from anywhere: availability subtracted only ScheduleLink's own
bookings, so the host's real calendar was invisible to the booking page and a
guest could book straight over an existing appointment.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Tuple
from zoneinfo import ZoneInfo

from ..models import CalendarConnection
from . import google_calendar, microsoft_calendar

logger = logging.getLogger(__name__)

BusyPeriod = Tuple[datetime, datetime]


def host_zone(tz_name=None) -> ZoneInfo:
    """Resolve the host's timezone, falling back to UTC rather than raising.

    Accepts the raw ``User.timezone`` column value without annotation so this
    doesn't trip SQLAlchemy's ``Column[str]`` typing.
    """
    try:
        return ZoneInfo(tz_name or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def utc_to_local_naive(dt: datetime, zone: ZoneInfo) -> datetime:
    """Convert a calendar API datetime (naive UTC) to naive host-local time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(zone).replace(tzinfo=None)


def overlaps(start: datetime, end: datetime, busy_periods: List[BusyPeriod]) -> bool:
    """Half-open overlap test: touching edges do not count as a conflict."""
    for busy_start, busy_end in busy_periods:
        if start < busy_end and end > busy_start:
            return True
    return False


async def external_busy_periods(
    db,
    user,
    start_local: datetime,
    end_local: datetime,
) -> List[BusyPeriod]:
    """Busy periods from the host's connected Google/Microsoft calendars.

    ``start_local``/``end_local`` are naive HOST-LOCAL datetimes describing the
    window to inspect (use the end of the last day you intend to inspect, i.e.
    midnight following it). Returns naive-local ``(start, end)`` tuples.

    Never raises. A calendar outage, an expired refresh token or a revoked
    grant degrades to "no external busy times" — the booking page keeps working
    instead of returning a 500, and the DB conflict check still applies.
    """
    zone = host_zone(getattr(user, "timezone", None))

    # The calendar APIs speak UTC; translate the local window into it.
    start_utc = start_local.replace(tzinfo=zone).astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.replace(tzinfo=zone).astimezone(timezone.utc).replace(tzinfo=None)

    connections = (
        db.query(CalendarConnection)
        .filter(
            CalendarConnection.user_id == user.id,
            CalendarConnection.is_active == True,  # noqa: E712
        )
        .all()
    )

    periods: List[BusyPeriod] = []
    for conn in connections:
        try:
            if conn.provider == "google":
                busy = await google_calendar.list_busy(conn, start_utc, end_utc, db)
            elif conn.provider == "microsoft":
                busy = await microsoft_calendar.list_busy(conn, start_utc, end_utc, db)
            else:
                continue
        except Exception as exc:  # noqa: BLE001 - must never break booking
            logger.error(
                "Busy lookup failed for %s connection %s (user %s): %s",
                conn.provider, conn.id, getattr(user, "id", "?"), exc,
            )
            continue

        for busy_start, busy_end in busy:
            periods.append(
                (utc_to_local_naive(busy_start, zone), utc_to_local_naive(busy_end, zone))
            )
    return periods
