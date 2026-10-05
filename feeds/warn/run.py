#!/usr/bin/env python3
"""WARN feed: scrape state WARN notices, keep a rolling window, push to vibeplat.

    python feeds/warn/run.py              scrape + push (token via env or local file)
    python feeds/warn/run.py --dry-run    scrape only; write app/dev-data/*.json for local UI work
    python feeds/warn/run.py --only CA,NY

Owner-data keys:
    warn.<ST>  {"code","name","url","notices":[...]}   one per state, newest first
    meta       {"checkedAt","windowDays","states":[{code,count,workers,latest,ok,error,failingSince,hash}]}

Exit status is 1 if any state failed, after pushing whatever succeeded, so a
broken parser shows up as a failed scheduled run without blanking the others.
"""

import argparse
import hashlib
import re
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


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_records(code, raw, prev, since, now):
    """Turn adapter rows into stable records, carrying `seen` forward from prev.

    prev is None on the very first run: everything gets seen=posted so the
    initial backfill doesn't all light up as "new".
    """
    prev_by_id = {r["id"]: r for r in prev or []}
    out, counts = {}, {}
    for r in raw:
        if not r.get("co") or not r.get("posted"):
            continue
        key = f"{code}|{norm(r['co'])}|{r['posted'].isoformat()}|{norm(r.get('addr') or r.get('loc'))}"
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > 1:  # genuinely separate notices with identical keys
            key += f"#{counts[key]}"
        rid = hashlib.sha1(key.encode()).hexdigest()[:10]
        old = prev_by_id.get(rid)
        posted = r["posted"]
        if old:
            seen = old["seen"]
        elif prev is None:
            seen = f"{posted.isoformat()}T12:00:00Z"
        else:
            seen = iso(now)
        if r.get("pm"):
            # Month-only source: once we've seen it, our first-seen day is the
            # best posted date available (if it falls inside that month).
            seen_day = datetime.fromisoformat(seen.replace("Z", "+00:00")).date()
            if prev is not None and (seen_day.year, seen_day.month) == (posted.year, posted.month):
                posted = seen_day
        if posted < since:
            continue
        eff = r.get("eff")
        rec = {
            "id": rid,
            "co": r["co"],
            "loc": r.get("loc") or "",
            "n": r.get("n"),
            "kind": r.get("kind") or "",
            "posted": posted.isoformat(),
            "eff": eff.isoformat() if hasattr(eff, "isoformat") else (eff or None),
            "seen": seen,
        }
        for opt in ("why", "ind"):
            if r.get(opt):
                rec[opt] = r[opt]
        if r.get("tmp"):
            rec["tmp"] = True
        if r.get("pm"):
            rec["pm"] = True
        out[rid] = rec

    # Keep earlier notices that dropped off the source only because the source
    # rolled over (older than anything it still lists), until they age out.
    oldest_listed = min((r["posted"] for r in raw if r.get("posted")), default=None)
    for rid, old in prev_by_id.items():
        if rid in out or old["posted"] < since.isoformat():
            continue
        if oldest_listed and old["posted"] < oldest_listed.isoformat():
            out[rid] = old

    return sorted(out.values(), key=lambda r: (r["posted"], r["seen"], r["co"]), reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="don't push or touch state; write app/dev-data")
    ap.add_argument("--only", help="comma-separated state codes")
    args = ap.parse_args()

    cfg = tomllib.loads((FEED_DIR / "feed.toml").read_text())
    now = datetime.now(timezone.utc)
    since = now.date() - timedelta(days=cfg["window_days"])
    codes = [c.strip().upper() for c in args.only.split(",")] if args.only else list(sources.ALL)

    http = http_session()
    health = load_json(STATE / "health.json", {})
    values, meta_states, failed = {}, [], []

    for code in sources.ALL:
        mod = sources.ALL[code]
        store_path = STATE / f"notices-{code}.json"
        prev = load_json(store_path, None)
        ok, error = True, None
        if code in codes:
            try:
                raw = mod.fetch(http, since)
                if not raw:
                    raise RuntimeError("source returned no rows")
                records = build_records(code, raw, prev, since, now)
                health.pop(code, None)
            except Exception as e:
                traceback.print_exc()
                ok, error = False, f"{type(e).__name__}: {e}"[:300]
                failed.append(code)
                health.setdefault(code, iso(now))
                records = [r for r in prev or [] if r["posted"] >= since.isoformat()]
        else:
            records = [r for r in prev or [] if r["posted"] >= since.isoformat()]
        if not args.dry_run:
            save_json(store_path, records)

        values[f"warn.{code}"] = {"code": code, "name": mod.NAME, "url": mod.URL, "notices": records}
        meta_states.append({
            "code": code,
            "name": mod.NAME,
            "url": mod.URL,
            "count": len(records),
            "workers": sum(r["n"] or 0 for r in records),
            "latest": records[0]["posted"] if records else None,
            "ok": ok,
            "error": error,
            "failingSince": health.get(code),
            "hash": digest(records),
        })
        status = "ok" if ok else f"FAILED ({error})"
        print(f"{code}: {len(records)} notices in window, {status}")

    meta = {"v": 1, "checkedAt": iso(now), "checkEveryHours": cfg["check_every_hours"],
            "windowDays": cfg["window_days"], "states": meta_states}

    if args.dry_run:
        DEV_DATA.mkdir(parents=True, exist_ok=True)
        # With --only, leave the other states' dev files (and meta) alone.
        out = {k: v for k, v in values.items() if k.split(".")[1] in codes}
        if not args.only:
            out["meta"] = meta
        for key, value in out.items():
            (DEV_DATA / f"{key}.json").write_text(dumps({"value": value, "updatedAt": iso(now)}))
        print(f"dry run: wrote {len(out)} files to {DEV_DATA.relative_to(FEED_DIR.parents[1])}")
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
        print(f"failed states: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
