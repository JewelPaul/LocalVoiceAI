import os
from pathlib import Path

# All file operations are sandboxed to this directory
_BASE = Path(__file__).parent.parent.parent / "workspace" / "files"


def _safe_path(name: str) -> Path:
    """Resolve name relative to workspace/files, preventing path traversal."""
    resolved = (_BASE / name).resolve()
    if not str(resolved).startswith(str(_BASE.resolve())):
        raise PermissionError(f"Path traversal detected: {name!r}")
    return resolved


def _ensure_base():
    _BASE.mkdir(parents=True, exist_ok=True)


def create_file(filename: str, content: str = "") -> str:
    _ensure_base()
    path = _safe_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def read_file(filename: str) -> str:
    _ensure_base()
    path = _safe_path(filename)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    return path.read_text(encoding="utf-8")


def write_file(filename: str, content: str) -> str:
    _ensure_base()
    path = _safe_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def delete_file(filename: str) -> str:
    """SENSITIVE: deletes a file from workspace/files."""
    _ensure_base()
    path = _safe_path(filename)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filename}")
    path.unlink()
    return f"Deleted: {filename}"


def create_folder(foldername: str) -> str:
    _ensure_base()
    path = _safe_path(foldername)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def list_directory(path: str = "") -> list[dict]:
    _ensure_base()
    target = _safe_path(path) if path else _BASE
    if not target.exists():
        raise FileNotFoundError(f"Directory not found: {path!r}")
    entries = []
    for item in sorted(target.iterdir()):
        entries.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
        })
    return entries
