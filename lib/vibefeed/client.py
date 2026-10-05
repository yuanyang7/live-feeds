import json
import os
from pathlib import Path

import requests

API = "https://vibeplat.ai/api/v1"

# Local fallback: the hub repo's gitignored token file ({"tokens": {handle: pat}}).
DEFAULT_TOKENS_FILE = Path.home() / "code" / "mini-games-hub" / ".vibeplat-tokens.json"


def resolve_token(account: str) -> str:
    """VIBEPLAT_TOKEN (CI) > VIBEPLAT_TOKEN_<ACCOUNT> > local tokens file."""
    env_key = "VIBEPLAT_TOKEN_" + account.upper().replace("-", "_")
    for key in ("VIBEPLAT_TOKEN", env_key):
        if os.environ.get(key):
            return os.environ[key]
    path = Path(os.environ.get("VIBEPLAT_TOKENS_FILE", DEFAULT_TOKENS_FILE))
    try:
        token = json.loads(path.read_text())["tokens"].get(account)
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        token = None
    if not token:
        raise SystemExit(f"No vibeplat token for account '{account}' (set ${env_key} or add it to {path})")
    return token


class VibeplatError(RuntimeError):
    pass


class Vibeplat:
    def __init__(self, token: str, base: str = API):
        self.base = base
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"

    def _check(self, r: requests.Response):
        if not r.ok:
            raise VibeplatError(f"{r.request.method} {r.url} -> {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else None

    def get(self, path: str, **kw):
        return self._check(self.s.get(self.base + path, timeout=60, **kw))

    def post(self, path: str, **kw):
        return self._check(self.s.post(self.base + path, timeout=300, **kw))

    def put(self, path: str, **kw):
        return self._check(self.s.put(self.base + path, timeout=120, **kw))

    def put_owner_data(self, slug: str, key: str, body: bytes):
        return self.put(
            f"/apps/{slug}/owner-data/{key}",
            data=body,
            headers={"Content-Type": "application/json"},
        )

    def owner_data_usage(self, slug: str):
        return self.get(f"/apps/{slug}/owner-data")
