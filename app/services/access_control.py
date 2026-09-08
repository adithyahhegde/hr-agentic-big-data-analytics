"""Request-scoped identity and lightweight tenant isolation for the API."""
from __future__ import annotations

from contextvars import ContextVar
import re

_CURRENT_USER: ContextVar[str] = ContextVar("hr_current_user", default="local")
_USER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@-]{0,63}$")


def set_current_user(user_id: str) -> None:
    """Set the authenticated request identity after validation."""
    value = str(user_id).strip()
    if not _USER_PATTERN.fullmatch(value):
        raise ValueError("Invalid user identity.")
    _CURRENT_USER.set(value)


def current_user() -> str:
    return _CURRENT_USER.get()


def validate_user_id(user_id: str) -> bool:
    return bool(_USER_PATTERN.fullmatch(str(user_id).strip()))
