import os
from pathlib import Path
from urllib.parse import urlparse

import requests

_BASE = Path(__file__).parent.parent.parent / "workspace" / "downloads"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def _ensure_base():
    _BASE.mkdir(parents=True, exist_ok=True)


def _safe_path(filename: str) -> Path:
    resolved = (_BASE / filename).resolve()
    if not str(resolved).startswith(str(_BASE.resolve())):
        raise PermissionError(f"Path traversal detected: {filename!r}")
    return resolved


def _derive_filename(url: str) -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    return name if name else "download"


def download_file(url: str, filename: str | None = None) -> str:
    """Download a file from URL into workspace/downloads. Returns saved path."""
    _ensure_base()
    if not filename:
        filename = _derive_filename(url)
    path = _safe_path(filename)

    with requests.get(url, headers=HEADERS, stream=True, timeout=30) as resp:
        resp.raise_for_status()
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

    return str(path)


def batch_download(urls: list[str]) -> list[dict]:
    """SENSITIVE: Download multiple files. Returns list of {url, path, status}."""
    _ensure_base()
    results = []
    for url in urls:
        try:
            path = download_file(url)
            results.append({"url": url, "path": path, "status": "success"})
        except Exception as e:
            results.append({"url": url, "path": None, "status": f"error: {e}"})
    return results
