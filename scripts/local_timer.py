#!/usr/bin/env python3
"""Gap-filler for one feed, meant to be driven by launchd on a laptop.

GitHub's scheduled runs start late and get dropped outright, so this runs the
same feed from this machine and only when the published data has actually gone
stale:

    python scripts/local_timer.py warn

It reads `meta.checkedAt` from vibeplat first and exits without touching the
sources unless the feed is overdue by the feed's own check_every_hours, so the
timer can fire every hour and still cost the sources nothing while Actions is
keeping up. If vibeplat can't be reached it runs anyway: a blip shouldn't stall
the feed.

State is committed and pushed like CI does. If that races with a CI run and the
rebase conflicts, the state commit is dropped (the data is already on vibeplat,
and the next run rebuilds state from origin).
"""

import argparse
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from vibefeed import Vibeplat, resolve_token  # noqa: E402


def log(msg: str):
    print(f"{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')} {msg}", flush=True)


def git(*args, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, check=check, capture_output=True, text=True)


def checked_minutes_ago(cfg) -> float | None:
    """Minutes since the published `meta.checkedAt`, or None if we couldn't tell."""
    try:
        entry = Vibeplat(resolve_token(cfg["account"])).get(f"/apps/{cfg['slug']}/owner-data/meta")
        checked = datetime.fromisoformat(entry["value"]["checkedAt"].replace("Z", "+00:00"))
    except Exception as e:
        log(f"couldn't read meta ({type(e).__name__}: {e}); running anyway")
        return None
    return (datetime.now(timezone.utc) - checked).total_seconds() / 60


def sync_state(feed: str):
    state = f"feeds/{feed}/state"
    git("add", state)
    if not git("diff", "--cached", "--quiet", check=False).returncode:
        log("state unchanged")
        return
    git("commit", "-q", "-m", f"chore({feed}): update feed state")
    for _ in range(3):
        if not git("pull", "--rebase", "-q", check=False).returncode and not git("push", "-q", check=False).returncode:
            log("state pushed")
            return
        git("rebase", "--abort", check=False)
    git("reset", "--hard", "-q", "origin/main", check=False)
    log("WARNING: couldn't push state; dropped the commit, next run rebuilds it from origin")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feed")
    ap.add_argument("--max-age-minutes", type=float,
                    help="skip the run if the feed was checked more recently than this "
                         "(default: the feed's check_every_hours, less 10 minutes)")
    args = ap.parse_args()

    cfg = tomllib.loads((ROOT / "feeds" / args.feed / "feed.toml").read_text())
    max_age = args.max_age_minutes
    if max_age is None:
        max_age = cfg["check_every_hours"] * 60 - 10
    age = checked_minutes_ago(cfg)
    if age is not None and age < max_age:
        log(f"{args.feed}: checked {age:.0f} min ago, skipping")
        return

    log(f"{args.feed}: checked {'?' if age is None else f'{age:.0f}'} min ago, running")
    git("pull", "--rebase", "--autostash", "-q", check=False)
    run = subprocess.run([sys.executable, str(ROOT / "feeds" / args.feed / "run.py")],
                         cwd=ROOT, capture_output=True, text=True)
    for line in (run.stdout + run.stderr).splitlines():
        log(f"  {line}")
    sync_state(args.feed)
    log(f"{args.feed}: exit {run.returncode}")
    sys.exit(run.returncode)


if __name__ == "__main__":
    main()
