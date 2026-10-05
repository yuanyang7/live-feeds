"""Helpers shared by the state adapters."""

import re


def kind_of(text) -> tuple[str, bool]:
    """('closure'|'layoff'|'', temporary?) from a free-text type column."""
    t = (text or "").lower()
    kind = "closure" if "clos" in t else "layoff" if "layoff" in t or "lay off" in t else ""
    return kind, "temp" in t


_STREET = re.compile(
    r"^.*?\b(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Way|Pl|Place|Ln|Lane|Ct|Court|"
    r"Pkwy|Parkway|Hwy|Highway|Cir|Circle|Ter|Terrace|Sq|Square|Plaza|Loop|Trl|Trail|Row|Broadway|Center)"
    r"\b\.?(?:\s+[NSEW]{1,2}\b\.?)?,?\s+",
    re.I,
)
_UNIT = re.compile(r"^(?:(?:Suite|Ste|Unit|Bldg|Building|Floor|Fl|Room|Rm|#)\.?\s*[\w-]+,?\s+|\d+(?:st|nd|rd|th)\s+Floor,?\s+)+", re.I)


def city_from_address(address: str, state: str) -> str:
    """'1 DNA Way  South San Francisco CA 94080' -> 'South San Francisco'; '' if unsure."""
    m = re.match(rf"(.*?)[\s,]+{state}\b[\s,]*\d{{5}}", address or "")
    if not m:
        return ""
    head = re.split(r"\s{2,}", m.group(1).strip(" ,"))[-1]
    if re.match(r"^\d", head):  # street still attached
        head = _STREET.sub("", head, count=1)
    head = _UNIT.sub("", head).strip(" ,")
    return "" if re.search(r"\d", head) or len(head) < 3 else head
