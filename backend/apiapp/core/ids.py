"""Internal ids and UTC time helpers."""

import re
import secrets
from datetime import UTC, datetime

_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
ID_RE = re.compile(r"^[a-z]{3}_[a-z0-9]{20}$")


def new_id(prefix: str) -> str:
    """`img_<20 chars>` / `ins_<20 chars>`: ~103 bits, lowercase alnum only (safe as a file name)."""
    return f"{prefix}_" + "".join(secrets.choice(_ALPHABET) for _ in range(20))


def is_valid_id(value: str, prefix: str) -> bool:
    return bool(ID_RE.match(value)) and value.startswith(f"{prefix}_")


def utcnow() -> datetime:
    """Aware UTC, truncated to milliseconds so values round-trip through MongoDB unchanged."""
    now = datetime.now(UTC)
    return now.replace(microsecond=now.microsecond // 1000 * 1000)


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
