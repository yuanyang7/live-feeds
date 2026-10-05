"""FDA Center for Veterinary Medicine "Outbreaks and Advisories": FDA's own
warnings ("Do Not Feed ..."). Some cover food the company never recalled, so they
don't appear in the recall table. The list page is plain HTML, one
"<date> - <link> <note>" paragraph per entry; an advisory that's been updated
appears once per update date.
"""

import re
import time

from bs4 import BeautifulSoup

from vibefeed import clean, parse_date

from .common import FDA, exclusion, hazard, parse_page, rid, species

CODE = "advisories"
NAME = "FDA pet food advisories"
URL = f"{FDA}/animal-veterinary/news-events/outbreaks-and-advisories"
ENTRY = re.compile(r"^(?:Updated\s+)?([A-Z][a-z]+\.? \d{1,2}, \d{4})\s*[-–—]\s*")


def _entries(http):
    """{url: {"title", "date" (first listed), "upd" (latest), "note"}} from the list page."""
    s = BeautifulSoup(http.get(URL).text, "html.parser")
    out = {}
    for p in (s.find("main") or s).find_all("p"):
        a = p.find("a", href=re.compile(r"/outbreaks-and-advisories/."))
        m = ENTRY.match(clean(p.get_text(" ")))
        day = parse_date(m.group(1).replace(".", "")) if m else None
        if not a or not day:
            continue
        url = FDA + a["href"] if a["href"].startswith("/") else a["href"]
        title = clean(a.get_text(" "))
        note = clean(p.get_text(" ").split(a.get_text(" ").strip(), 1)[-1]).strip(" -–—()")
        e = out.setdefault(url, {"title": title, "date": day, "upd": day, "note": ""})
        e["date"], e["upd"] = min(e["date"], day), max(e["upd"], day)
        if day == e["upd"] and note.lower() != "updated":
            e["note"] = note
    return out


def _reason(title: str) -> str:
    m = re.search(r"\b(?:Due to|Because of|for)\s+(.+)$", title)
    return m.group(1) if m else ""


def fetch(http, since, known):
    out = []
    for url, e in _entries(http).items():
        if e["upd"] < since:
            continue
        id_ = rid(url)
        old = known.get(id_)
        rec = {
            "id": id_,
            "kind": "advisory",
            "date": e["date"].isoformat(),
            "url": url,
            "title": e["title"],
            "why": _reason(e["title"]),
        }
        if e["upd"] != e["date"]:
            rec["upd"] = e["upd"].isoformat()
        if e["note"]:
            rec["note"] = e["note"]
            if "terminated" in e["note"].lower():
                rec["done"] = True
        page = None
        if old and old.get("det") and old.get("upd", old["date"]) == rec.get("upd", rec["date"]):
            page = {k: old[k] for k in ("sum", "lots", "ill") if k in old}
        else:
            try:
                time.sleep(1)
                page = parse_page(http.get(url).text, url)
            except Exception as ex:
                print(f"  page failed, will retry: {url} ({type(ex).__name__}: {ex})")
        body = ""
        if page:
            body = page.get("body", "")
            rec.update({k: page[k] for k in ("sum", "lots", "ill") if page.get(k)})
            rec["det"] = True
        head = " ".join((rec["title"], rec.get("sum", "")))
        if old and not body:
            rec["sp"] = old.get("sp", [])
            if old.get("x"):
                rec["x"] = old["x"]
        else:
            x = exclusion(head, body)
            if x:
                rec["x"] = x
            rec["sp"] = species(head, body)
        rec["hz"] = hazard(rec["title"] + " " + rec.get("sum", ""))
        out.append(rec)
    return out
