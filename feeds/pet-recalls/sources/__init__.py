"""One module per source. Each exposes CODE (its owner-data key), NAME, URL (the
human-facing page) and fetch(http, since, known) -> list of records:

    {"id", "kind": "recall"|"advisory", "date", "url", "why", "hz", "sp",
     optional "upd", "title", "brand", "product", "co", "sum", "lots", "ill",
     "tel", "img", "note", "done",
     state-only "det" (page was read) and "x" (why it isn't a dog/cat food item)}

`known` maps id -> the record stored last run, so pages are read once.
"""

from . import fda_advisories, fda_recalls

ALL = {m.CODE: m for m in (fda_recalls, fda_advisories)}
