"""Washington ESD: a paged ASP.NET table, newest first. We page only until we
pass the feed's window instead of walking all ~100 pages."""

from bs4 import BeautifulSoup

from vibefeed import clean, parse_date, parse_int

from .common import kind_of

CODE = "WA"
NAME = "Washington"
URL = "https://esd.wa.gov/employer-requirements/layoffs-and-employee-notifications/worker-adjustment-and-retraining-notification-warn-layoff-and-closure-database"
SEARCH_URL = "https://fortress.wa.gov/esd/file/warn/Public/SearchWARN.aspx"
MAX_PAGES = 12


def _rows(soup):
    table = soup.find("table")
    out = []
    for tr in table.find_all("tr"):
        cells = [clean(td.get_text(" ")) for td in tr.find_all("td")]
        # Data rows have 8 cells; the pager row is a single cell.
        if len(cells) == 8 and parse_date(cells[6]):
            out.append(cells)
    return out


def fetch(http, since):
    rows = []
    soup = BeautifulSoup(http.get(SEARCH_URL).text, "html.parser")
    for page in range(2, MAX_PAGES + 2):
        page_rows = _rows(soup)
        if not page_rows:
            break
        for co, loc, start, n, typ, perm, recv, _notice in page_rows:
            kind, _ = kind_of(typ)
            rows.append({
                "co": co,
                "loc": loc,
                "n": parse_int(n),
                "kind": kind,
                "tmp": "temp" in perm.lower(),
                "posted": parse_date(recv),
                "eff": parse_date(start),
            })
        if min(parse_date(r[6]) for r in page_rows) < since:
            break
        form = {i["name"]: i.get("value", "") for i in soup.find_all("input", attrs={"name": True})
                if i["name"].startswith("__")}
        form.update({"__EVENTTARGET": "ucPSW$gvMain", "__EVENTARGUMENT": f"Page${page}"})
        soup = BeautifulSoup(http.post(SEARCH_URL, data=form).text, "html.parser")
    if not rows:
        raise RuntimeError("no rows parsed from the ESD table")
    return rows
