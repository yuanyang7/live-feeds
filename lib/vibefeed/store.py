import hashlib
import json
from pathlib import Path


def dumps(value) -> str:
    """Compact, key-sorted JSON so the same data always hashes the same."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def digest(value) -> str:
    return hashlib.sha256(dumps(value).encode()).hexdigest()[:16]


def load_json(path: Path, default):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default


def save_json(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Indented for readable git diffs of committed state.
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
