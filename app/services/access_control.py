"""Request-scoped identity and lightweight tenant isolation for the API."""
from __future__ import annotations

from contextvars import ContextVar, Token
import re
import secrets

_CURRENT_USER: ContextVar[str] = ContextVar("hr_current_user", default="local")
_USER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@-]{0,63}$")


def set_current_user(user_id: str) -> Token[str]:
    """Set the authenticated request identity after validation."""
    value = str(user_id).strip()
    if not _USER_PATTERN.fullmatch(value):
        raise ValueError("Invalid user identity.")
    return _CURRENT_USER.set(value)


def reset_current_user(token: Token[str]) -> None:
    """Restore the previous request identity when a request completes."""
    _CURRENT_USER.reset(token)


def current_user() -> str:
    return _CURRENT_USER.get()


def validate_user_id(user_id: str) -> bool:
    return bool(_USER_PATTERN.fullmatch(str(user_id).strip()))


def authenticate_api_key(
    supplied_key: str,
    shared_key: str,
    user_keys: tuple[tuple[str, str], ...] = (),
) -> str | None:
    """Resolve a credential to an authenticated user without trusting client user headers.

    When per-user credentials are configured they take precedence over the legacy
    single shared key. Comparisons use constant-time equality.
    """
    if user_keys:
        for user_id, expected_key in user_keys:
            if validate_user_id(user_id) and secrets.compare_digest(supplied_key, expected_key):
                return user_id
        return None
    if shared_key and secrets.compare_digest(supplied_key, shared_key):
        return "local"
    return None
