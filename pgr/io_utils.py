import json
from pathlib import Path

from .errors import PaperGraphError


def json_bytes(value):
    """Return canonical, newline-terminated JSON bytes."""
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))
    return path


def read_json(path):
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise PaperGraphError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PaperGraphError(f"Invalid JSON in {path}: {exc.msg} at line {exc.lineno}, column {exc.colno}") from exc


def resolve_json_path(path, filename):
    path = Path(path)
    return path / filename if path.is_dir() else path
