#!/usr/bin/env python3
"""Pet recalls feed: FDA dog/cat food recalls and advisories, pushed to vibeplat.

    python feeds/pet-recalls/run.py              scrape + push (token via env or local file)
    python feeds/pet-recalls/run.py --dry-run    scrape only; write app/dev-data/*.json for local UI work

Owner-data keys:
    recalls     {"name","url","items":[...]}   FDA recall announcements for dog/cat food, newest first
    advisories  {"name","url","items":[...]}   FDA "do not feed" advisories
    meta        {"checkedAt","checkEveryHours","windowDays","sources":[{code,name,url,count,latest,ok,error,failingSince,hash}]}

state/<key>.json keeps every candidate the source listed in the window, including
ones ruled out as not dog/cat food (marked "x"), so announcement pages are read
once. Exit status is 1 if a source failed, after pushing whatever succeeded.
"""

import argparse
import sys
import tomllib
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

FEED_DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(FEED_DIR.parents[1] / "lib"), str(FEED_DIR)]

import sources  # noqa: E402
from vibefeed import Vibeplat, digest, dumps, http_session, load_json, push_keys, resolve_token, save_json  # noqa: E402

STATE = FEED_DIR / "state"
DEV_DATA = FEED_DIR / "app" / "dev-data"
STATE_ONLY = ("det", "x")


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def last_date(r) -> str:
    return r.get("upd") or r["date"]


def stamp(records, prev, now):
    """Carry `seen` forward. On the first run everything is dated by its own
    announcement, so the backfill doesn't all show up as new."""
    prev_by_id = {r["id"]: r for r in prev or []}
    for r in records:
        old = prev_by_id.get(r["id"])
        if old:
            r["seen"] = old["seen"]
        elif prev is None:
            r["seen"] = f"{r['date']}T12:00:00Z"
        else:
            r["seen"] = iso(now)
    return sorted(records, key=lambda r: (last_date(r), r["seen"], r["id"]), reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="don't push or touch state; write app/dev-data")
    args = ap.parse_args()

    cfg = tomllib.loads((FEED_DIR / "feed.toml").read_text())
    now = datetime.now(timezone.utc)
    since = now.date() - timedelta(days=cfg["window_days"])

    http = http_session()
    health = {k: v for k, v in load_json(STATE / "health.json", {}).items() if k in sources.ALL}
    values, meta_sources, failed = {}, [], []

    for code, mod in sources.ALL.items():
        store_path = STATE / f"{code}.json"
        prev = load_json(store_path, None)
        ok, error = True, None
        try:
            records = mod.fetch(http, since, {r["id"]: r for r in prev or []})
            if not records:
                raise RuntimeError("source listed nothing in the window")
            records = stamp(records, prev, now)
            health.pop(code, None)
        except Exception as e:
            traceback.print_exc()
            ok, error = False, f"{type(e).__name__}: {e}"[:300]
            failed.append(code)
            health.setdefault(code, iso(now))
            records = [r for r in prev or [] if last_date(r) >= since.isoformat()]
        if not args.dry_run:
            save_json(store_path, records)

        items = [{k: v for k, v in r.items() if k not in STATE_ONLY} for r in records if not r.get("x")]
        values[code] = {"name": mod.NAME, "url": mod.URL, "items": items}
        meta_sources.append({
            "code": code,
            "name": mod.NAME,
            "url": mod.URL,
            "count": len(items),
            "latest": last_date(items[0]) if items else None,
            "ok": ok,
            "error": error,
            "failingSince": health.get(code),
            "hash": digest(items),
        })
        skipped = len(records) - len(items)
        print(f"{code}: {len(items)} dog/cat items ({skipped} other animal/drug skipped), "
              f"{'ok' if ok else f'FAILED ({error})'}")

    meta = {"v": 1, "checkedAt": iso(now), "checkEveryHours": cfg["check_every_hours"],
            "windowDays": cfg["window_days"], "sources": meta_sources}

    if args.dry_run:
        DEV_DATA.mkdir(parents=True, exist_ok=True)
        for key, value in {**values, "meta": meta}.items():
            (DEV_DATA / f"{key}.json").write_text(dumps({"value": value, "updatedAt": iso(now)}))
        sizes = {k: len(dumps(v).encode()) for k, v in values.items()}
        print(f"dry run: wrote {len(values) + 1} files to {DEV_DATA.relative_to(FEED_DIR.parents[1])} "
              f"({', '.join(f'{k} {n:,} B' for k, n in sizes.items())})")
    else:
        client = Vibeplat(resolve_token(cfg["account"]))
        pushed = load_json(STATE / "pushed.json", {})
        sent = push_keys(client, cfg["slug"], values, pushed)
        # meta goes last so its hashes never point at data viewers can't fetch yet;
        # it carries checkedAt, so it's pushed every run and not tracked in pushed.json.
        client.put_owner_data(cfg["slug"], "meta", dumps(meta).encode())
        save_json(STATE / "pushed.json", pushed)
        save_json(STATE / "health.json", health)
        print(f"pushed: {', '.join(sent + ['meta'])}")

    if failed:
        print(f"failed sources: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
