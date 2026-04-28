from __future__ import annotations

from datetime import date, datetime
from typing import Any

def format_slot(dt_value: Any) -> str:
    if dt_value is None:
        return "-"
    if isinstance(dt_value, str):
        try:
            dt_value = datetime.fromisoformat(dt_value)
        except ValueError:
            return dt_value
    return dt_value.strftime("%b %d, %Y %I:%M %p")

def pet_avatar(species: str | None) -> str:
    avatars = {
        "dog": "🐕",
        "cat": "🐈",
        "rabbit": "🐇",
        "bird": "🐦",
        "hamster": "🐹",
        "fish": "🐠",
        "reptile": "🦎",
    }
    return avatars.get((species or "").lower(), "🐾")

def parse_date(value: str | None, default: date | None = None) -> date:
    if value:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            pass
    return default or date.today()

def safe_int(value: str | None, default: int | None = None) -> int | None:
    if value in {None, ""}:
        return default
    if not isinstance(value, str):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None

def is_checked(value: str | None) -> bool:
    return value in {"1", "true", "on", "yes"}
