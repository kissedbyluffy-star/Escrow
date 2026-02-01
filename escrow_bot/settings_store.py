from __future__ import annotations

from typing import Any

from escrow_bot import db


def get_setting(conn, key: str, default: str | None = None) -> str | None:
    row = db.fetch_one(conn, "SELECT value FROM settings WHERE key=?", (key,))
    if row:
        return row["value"]
    return default


def set_setting(conn, key: str, value: Any) -> None:
    db.execute(
        conn,
        """
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        (key, str(value)),
    )


def toggle_setting(conn, key: str, default: bool = False) -> bool:
    current = get_setting(conn, key, str(default))
    new_value = "false" if str(current).lower() == "true" else "true"
    set_setting(conn, key, new_value)
    return new_value == "true"


def get_bool(conn, key: str, default: bool = False) -> bool:
    value = get_setting(conn, key, str(default))
    return str(value).lower() == "true"


def get_int(conn, key: str, default: int = 0) -> int:
    value = get_setting(conn, key, str(default))
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_float(conn, key: str, default: float = 0.0) -> float:
    value = get_setting(conn, key, str(default))
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def ensure_defaults(conn, defaults: dict[str, Any]) -> None:
    for key, value in defaults.items():
        if get_setting(conn, key) is None:
            set_setting(conn, key, value)
