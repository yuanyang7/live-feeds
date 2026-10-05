import re
from datetime import date, datetime

_DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%Y-%m-%d %H:%M:%S", "%m-%d-%Y", "%B %d, %Y")


def parse_date(value) -> date | None:
    """Best-effort date from a spreadsheet cell or string; None if it isn't one."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    # "2026-09-30T00:00:00" and similar
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
        return date.fromisoformat(m.group(1))
    return None


def parse_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else None


def clean(value) -> str:
    """Collapse whitespace; '' for empty cells."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()
