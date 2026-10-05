"""Push app-wide values to vibeplat owner-data, skipping anything unchanged."""

import re

from .client import Vibeplat
from .store import digest, dumps

# Platform limits (GET /api/v1/apps/{slug}/owner-data reports the live ones).
MAX_VALUE_BYTES = 256 * 1024
MAX_KEYS = 32
MAX_APP_BYTES = 1024 * 1024
KEY_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


def check_limits(values: dict) -> dict[str, int]:
    sizes = {k: len(dumps(v).encode()) for k, v in values.items()}
    for k, n in sizes.items():
        if not KEY_RE.match(k):
            raise ValueError(f"owner-data key {k!r} has characters outside [A-Za-z0-9._:-]")
        if n > MAX_VALUE_BYTES:
            raise ValueError(f"owner-data key {k!r} is {n:,} bytes (limit {MAX_VALUE_BYTES:,})")
    if len(sizes) > MAX_KEYS:
        raise ValueError(f"{len(sizes)} owner-data keys (limit {MAX_KEYS})")
    if sum(sizes.values()) > MAX_APP_BYTES:
        raise ValueError(f"owner-data totals {sum(sizes.values()):,} bytes (limit {MAX_APP_BYTES:,})")
    return sizes


def push_keys(client: Vibeplat | None, slug: str, values: dict, pushed: dict, always=()) -> list[str]:
    """PUT each value whose digest differs from `pushed` (updated in place).

    Keys in `always` are pushed regardless (e.g. a heartbeat). With client=None
    nothing is sent and the would-be pushes are returned (dry run).
    """
    check_limits(values)
    sent = []
    for key, value in values.items():
        d = digest(value)
        if pushed.get(key) == d and key not in always:
            continue
        if client is not None:
            client.put_owner_data(slug, key, dumps(value).encode())
            pushed[key] = d
        sent.append(key)
    return sent
