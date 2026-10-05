#!/usr/bin/env python3
"""Publish a feed's web app to vibeplat (create on first run, then new builds).

    python scripts/publish_app.py warn            upload a new build (patch bump)
    python scripts/publish_app.py warn --listing  also push listing text, tags, translations, icon, banner

Reads feeds/<feed>/feed.toml (slug, account) and feeds/<feed>/listing/listing.json.
The zip is feeds/<feed>/app/ minus dev-data/.
"""

import argparse
import io
import json
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from vibefeed import Vibeplat, resolve_token  # noqa: E402
from vibefeed.client import VibeplatError  # noqa: E402

LISTING_FIELDS = ("name", "tagline", "description", "remixExamplePrompts", "primaryLocale")


def build_zip(app_dir: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(app_dir.rglob("*")):
            rel = p.relative_to(app_dir)
            if p.is_dir() or rel.parts[0] == "dev-data" or p.name.startswith("."):
                continue
            z.write(p, rel.as_posix())
    return buf.getvalue()


def next_version(client, slug) -> str:
    try:
        versions = client.get(f"/apps/{slug}/versions")
    except VibeplatError:
        return "1.0.0"
    items = versions.get("versions", versions) if isinstance(versions, dict) else versions
    best = (0, 0, 0)
    for v in items or []:
        try:
            best = max(best, tuple(int(x) for x in str(v["version"]).split(".")[:3]))
        except (KeyError, ValueError):
            pass
    if best == (0, 0, 0):
        return "1.0.0"
    return f"{best[0]}.{best[1]}.{best[2] + 1}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feed")
    ap.add_argument("--listing", action="store_true", help="also update listing, tags, translations, images")
    args = ap.parse_args()

    feed_dir = ROOT / "feeds" / args.feed
    cfg = tomllib.loads((feed_dir / "feed.toml").read_text())
    listing = json.loads((feed_dir / "listing" / "listing.json").read_text())
    slug = cfg["slug"]
    client = Vibeplat(resolve_token(cfg["account"]))

    me = client.get("/me")
    print(f"account: {me.get('username')}")

    try:
        client.get(f"/apps/{slug}")
        created = False
    except VibeplatError as e:
        if "404" not in str(e):
            raise
        body = {k: listing[k] for k in ("name", "tagline", "description", "tags", "remixExamplePrompts", "ageRating")}
        body.update(type="WEB", pricingModel="FREE", slug=slug)
        res = client.post("/apps", json=body)
        print(f"created app: {res.get('slug', slug)} {res.get('warnings') or ''}")
        if res.get("slug") and res["slug"] != slug:
            # vibeplat may suffix the requested slug; it's permanent, so record it.
            toml = feed_dir / "feed.toml"
            toml.write_text(toml.read_text().replace(f'slug = "{slug}"', f'slug = "{res["slug"]}"'))
            slug = res["slug"]
            print(f"vibeplat assigned slug {slug!r}; feed.toml updated")
        created = True

    if args.listing or created:
        client.s.patch(client.base + f"/apps/{slug}/metadata",
                       json={k: listing[k] for k in LISTING_FIELDS if k in listing}, timeout=60).raise_for_status()
        client.put(f"/apps/{slug}/tags", json={"tags": listing["tags"]})
        if listing.get("translations"):
            client.put(f"/apps/{slug}/translations", json={"translations": listing["translations"]})
        for kind in ("icon", "banner"):
            img = feed_dir / "listing" / f"{kind}.png"
            if img.exists():
                client.post(f"/apps/{slug}/{kind}", data=img.read_bytes(), headers={"Content-Type": "image/png"})
        print("listing updated")

    version = next_version(client, slug)
    data = build_zip(feed_dir / "app")
    res = client.post(
        f"/apps/{slug}/artifact",
        params={"platform": "WEB", "fileName": f"{slug}-{version}.zip", "version": version},
        data=data,
        headers={"Content-Type": "application/zip"},
    )
    status = res.get("status") or res.get("app", {}).get("status")
    print(f"uploaded {version} ({len(data):,} bytes): {status or json.dumps(res)[:300]}")
    print(f"https://vibeplat.ai/apps/{slug}")


if __name__ == "__main__":
    main()
