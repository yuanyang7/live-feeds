"""New York DOL: the Tableau dashboard's CSV export (same trick as Big Local
News' warn-scraper). Covers the current year."""

import csv
import io
import re

from vibefeed import clean, parse_date, parse_int

from .common import city_from_address, kind_of

CODE = "NY"
NAME = "New York"
URL = "https://dol.ny.gov/warn-notices"
CSV_URL = (
    "https://public.tableau.com/views/WorkerAdjustmentRetrainingNotificationWARN/WARN.csv"
    "?:showVizHome=n&:embed=y"
)


def fetch(http, since):
    text = http.get(CSV_URL).content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = [clean(h).lower() for h in next(reader)]
    col = lambda *keys: next(i for i, h in enumerate(header) if all(k in h for k in keys))
    i_co, i_start, i_posted = col("business"), col("starts"), col("posted")
    i_notice, i_addr, i_county = col("date of warn"), col("address"), col("county")
    i_type, i_perm, i_why, i_n = col("layoff or closure"), col("permanent"), col("reason"), col("affected")
    rows = []
    for r in reader:
        if len(r) <= i_n or not clean(r[i_co]):
            continue
        kind, _ = kind_of(r[i_type])
        addr = clean(r[i_addr])
        why = clean(r[i_why])
        rows.append({
            "co": clean(r[i_co]),
            "loc": city_from_address(addr, "NY") or clean(r[i_county]),
            "n": parse_int(r[i_n]),
            "kind": kind,
            "tmp": "temp" in r[i_perm].lower(),
            "posted": parse_date(r[i_posted]) or parse_date(r[i_notice]),
            "eff": parse_date(r[i_start]),
            "why": "" if why.lower() in ("other", "n/a") else why,
            "addr": addr,
        })
    return rows
