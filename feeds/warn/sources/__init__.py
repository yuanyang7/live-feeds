"""One module per state. Each exposes CODE, NAME, URL (the human-facing source
page) and fetch(http, since) -> list of raw notices:

    {"co": str, "loc": str, "n": int|None, "kind": "layoff"|"closure"|"",
     "tmp": bool, "posted": date, "eff": date|str|None,
     optional "why", "ind", "pm" (posted date is month-only), "addr" (for ids)}

`since` is the oldest posted date the feed keeps; adapters may use it to
fetch less, but returning older rows is fine (run.py filters).
"""

from . import ca, nj, ny, tx, wa

ALL = {m.CODE: m for m in (ca, ny, tx, wa, nj)}
