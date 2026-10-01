"""Pure geofence logic. No DB, no HTTP — easy to test in isolation.

- haversine_meters: great-circle distance, meters
- is_within_schedule: (days + HH:MM range, handles overnight)
- evaluate_position: combines both, returns inside + entered/exited
"""
import math
from datetime import datetime
from typing import Optional

EARTH_RADIUS_M = 6371008.8
_DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters. Numerically stable (atan2)."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    )
    a = min(1.0, max(0.0, a))  # clamp for float safety
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def _parse_hhmm(s: str) -> int:
    """'07:30' -> 450 (minutes since midnight). Raises ValueError."""
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError(f"bad time: {s!r}")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"bad time: {s!r}")
    return h * 60 + m


def is_within_schedule(
    schedule: Optional[dict], at_utc: datetime
) -> bool:
    """Return True if `at_utc` is inside the schedule window.

    schedule=None -> always True (24/7).
    schedule={days, start_time, end_time}:
      - days: list of 'mon'..'sun'
      - times in HH:MM (UTC)
      - start > end means the window wraps midnight (e.g. 22:00-06:00)
    """
    if schedule is None:
        return True

    day = _DAYS[at_utc.weekday()]
    if day not in schedule.get("days", []):
        return False

    start = _parse_hhmm(schedule["start_time"])
    end = _parse_hhmm(schedule["end_time"])
    now = at_utc.hour * 60 + at_utc.minute

    if start <= end:
        return start <= now <= end
    # wraps midnight
    return now >= start or now <= end


def evaluate_position(
    *,
    center_lat: float,
    center_lon: float,
    radius_meters: float,
    latitude: float,
    longitude: float,
    at_utc: datetime,
    schedule: Optional[dict],
    was_inside: bool,
    enabled: bool = True,
) -> dict:
    """Return a deterministic evaluation dict.

    {
      "distance_meters": float,
      "within_radius": bool,
      "within_schedule": bool,
      "inside": bool,          # enabled AND within_radius AND within_schedule
      "entered": bool,         # was_inside=False -> inside=True
      "exited": bool,          # was_inside=True  -> inside=False
      "enabled": bool,
    }
    """
    distance = haversine_meters(
        center_lat, center_lon, latitude, longitude
    )
    within_radius = distance <= radius_meters
    within_sched = is_within_schedule(schedule, at_utc)

    inside = bool(enabled) and within_radius and within_sched

    entered = (not was_inside) and inside
    exited = was_inside and (not inside)

    return {
        "distance_meters": round(distance, 3),
        "within_radius": within_radius,
        "within_schedule": within_sched,
        "inside": inside,
        "entered": entered,
        "exited": exited,
        "enabled": bool(enabled),
    }
