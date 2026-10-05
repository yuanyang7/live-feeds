"""FDA "Recalls, Market Withdrawals, & Safety Alerts": the company announcements
FDA posts. The page's table loads from a Drupal datatables endpoint that answers
plain GETs with JSON, newest first.

The table's "Animal & Veterinary" filter misses some pet food recalls (Wild Coast
Raw's bird flu recall, March 2025), so this reads every product type back to
`since` and picks pet food out by its product-type tags and wording.

The table is served by more than one search backend behind a load balancer, and
they don't always agree: in October 2026 one of two was missing 17 rows, Wild
Coast Raw's among them. A session sticks to one backend (AWSALB cookie), so
_rows asks on a few fresh sessions and pages through the one listing the most.
"""

import html
import re
import time

from vibefeed import clean, http_session, parse_date

from .common import FDA, exclusion, hazard, parse_page, rid, species

CODE = "recalls"
NAME = "FDA recall announcements"
URL = f"{FDA}/safety/recalls-market-withdrawals-safety-alerts"
TABLE = f"{FDA}/datatables/views/ajax"
PARAMS = {
    "search_api_fulltext": "",
    "field_regulated_product_field": "All",
    "field_terminated_recall": "All",
    "view_name": "recall_solr_index",
    "view_display_id": "recall_datatable_block_1",
    "_drupal_ajax": "1",
    "draw": "1",
}
PAGE = 250
PROBES = 4
CANDIDATE = re.compile(r"\b(?:pet|dogs?|cats?|canine|feline|pupp(?:y|ies)|kittens?)\b", re.I)


def _text(cell: str) -> str:
    return clean(html.unescape(re.sub(r"<[^>]+>", " ", cell or "")))


def _fullest(http):
    """The session whose backend lists the most rows: `http` first, then fresh
    sessions until two backends disagree (the bigger one wins) or PROBES run out."""
    best, best_total, seen = None, -1, set()
    for i in range(PROBES):
        s = http if i == 0 else http_session()
        total = int(s.get(TABLE, params={**PARAMS, "start": 0, "length": 1}).json().get("recordsFiltered") or 0)
        seen.add(total)
        if total > best_total:
            best, best_total = s, total
        if len(seen) > 1:
            break
    return best


def _rows(http, since):
    """Table rows newer than `since`, paging until the window is covered."""
    http = _fullest(http)
    start = 0
    while True:
        data = http.get(TABLE, params={**PARAMS, "start": start, "length": PAGE}).json()
        rows = data.get("data") or []
        for r in rows:
            day = parse_date(_text(r[0]))
            href = re.search(r'href="([^"]+)"', r[1] or "")
            if day and href:
                yield {
                    "date": day,
                    "url": FDA + href.group(1) if href.group(1).startswith("/") else href.group(1),
                    "brand": _text(r[1]),
                    "product": _text(r[2]),
                    "types": _text(r[3]),
                    "why": _text(r[4]),
                    "co": _text(r[5]),
                    "done": "terminated" in _text(r[6]).lower(),
                }
        start += len(rows)
        oldest = parse_date(_text(rows[-1][0])) if rows else None
        if not rows or start >= int(data.get("recordsFiltered") or 0) or (oldest and oldest < since):
            return


def fetch(http, since, known):
    """Pet food recalls since `since`. `known` (id -> stored record) saves
    refetching announcement pages; a page is read once, or again if FDA re-dates it."""
    out = []
    for row in _rows(http, since):
        if row["date"] < since:
            continue
        line = " ".join((row["brand"], row["product"], row["why"]))
        if "Animal & Veterinary" not in row["types"] and "Pet Food" not in row["types"] and not CANDIDATE.search(line):
            continue
        id_ = rid(row["url"])
        old = known.get(id_)
        rec = {
            "id": id_,
            "kind": "recall",
            "date": row["date"].isoformat(),
            "url": row["url"],
            "brand": row["brand"],
            "product": row["product"],
            "co": row["co"],
            "why": row["why"],
        }
        if row["done"]:
            rec["done"] = True
        page = None
        if old and old.get("det") and old["date"] == rec["date"]:
            page = {k: old[k] for k in ("title", "sum", "lots", "ill", "tel", "img") if k in old}
            page["body"] = ""
        else:
            try:
                time.sleep(1)  # announcement pages are fetched one at a time, once each
                page = parse_page(http.get(row["url"]).text, row["url"])
            except Exception as e:  # keep the table's data; the page is retried next run
                print(f"  page failed, will retry: {row['url']} ({type(e).__name__}: {e})")
        if page:
            rec.update({k: v for k, v in page.items() if k != "body" and v})
            rec["det"] = True
        head = " ".join((rec.get("title", ""), line, rec.get("sum", "")))
        body = (page or {}).get("body", "")
        if old and not body:
            # Reused page: exclusion and species were settled when it was read.
            rec["sp"] = old.get("sp", [])
            if old.get("x"):
                rec["x"] = old["x"]
        else:
            x = exclusion(head, body, row["types"])
            if x:
                rec["x"] = x
            rec["sp"] = species(head, body)
        rec["hz"] = hazard(rec["why"] + " " + rec.get("title", ""))
        out.append(rec)
    return out
