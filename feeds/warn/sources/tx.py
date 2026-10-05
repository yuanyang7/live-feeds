"""Texas Workforce Commission: one spreadsheet per year; we read the latest two."""

import io
import re
from datetime import date

from openpyxl import load_workbook

from vibefeed import clean, parse_date, parse_int

CODE = "TX"
NAME = "Texas"
URL = "https://www.twc.texas.gov/data-reports/warn-notice"
# TWC's firewall challenges browser-like UAs (it expects JS) but serves plain
# clients, so identify honestly instead.
HEADERS = {"User-Agent": "live-feeds/1.0 (WARN notice tracker; +https://github.com/yuanyang7/live-feeds)"}


def fetch(http, since):
    resp = http.get(URL, headers=HEADERS)
    html = resp.text
    links = {}
    for href in re.findall(r'href="(/sites/default/files/[^"]*warn-act-listings-(\d{4})[^"]*\.xlsx)"', html):
        links[int(href[1])] = href[0]
    if not links:
        # The page is behind a bot challenge from datacenter IPs (empty 202); the
        # spreadsheets live at a stable path, so try this year's and last year's.
        year = date.today().year
        links = {y: f"/sites/default/files/oei/docs/warn-act-listings-{y}-twc.xlsx" for y in (year - 1, year)}
    rows = []
    for year in sorted(links)[-2:]:
        xr = http.get("https://www.twc.texas.gov" + links[year], headers=HEADERS)
        if xr.status_code != 200 or not xr.content.startswith(b"PK"):
            raise RuntimeError(f"TWC page (HTTP {resp.status_code}) and {year} spreadsheet "
                               f"(HTTP {xr.status_code}, {len(xr.content)} bytes) both blocked")
        wb = load_workbook(io.BytesIO(xr.content), read_only=True, data_only=True)
        it = wb.worksheets[0].iter_rows(values_only=True)
        header = [clean(h).upper() for h in next(it)]
        col = header.index
        i_notice, i_co, i_county, i_n = col("NOTICE_DATE"), col("JOB_SITE_NAME"), col("COUNTY_NAME"), col("TOTAL_LAYOFF_NUMBER")
        i_eff, i_recv, i_city = col("LAYOFF_DATE"), col("WFDD_RECEIVED_DATE"), col("CITY_NAME")
        for r in it:
            if not r or not r[i_co]:
                continue
            rows.append({
                "co": clean(r[i_co]),
                "loc": clean(r[i_city]) or clean(r[i_county]),
                "n": parse_int(r[i_n]),
                "kind": "",  # TWC doesn't say
                "tmp": False,
                "posted": parse_date(r[i_recv]) or parse_date(r[i_notice]),
                "eff": parse_date(r[i_eff]),
            })
    return rows
