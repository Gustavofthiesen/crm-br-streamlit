"""Timezone helpers isolated to avoid import cycles."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .config import get_timezone_name


def br_now() -> datetime:
    return datetime.now(ZoneInfo(get_timezone_name())).replace(tzinfo=None)
