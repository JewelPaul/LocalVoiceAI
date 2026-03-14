import os
from pathlib import Path
from urllib.parse import urlparse, urlencode

import requests
from bs4 import BeautifulSoup

_BASE = Path(__file__).parent.parent.parent / "workspace" / "downloads"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def image_search(query: str, max_results: int = 5) -> list[str]:
    """Search DuckDuckGo for images. Returns list of image URLs."""
    # Use DuckDuckGo image search API
    params = {
        "q": query,
        "iax": "images",
        "ia": "images",
    }
    search_url = "https://duckduckgo.com/?" + urlencode(params)
    try:
        # First request to get a vqd token
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        vqd = ""
        for line in resp.text.splitlines():
            if "vqd=" in line:
                import re
                match = re.search(r'vqd=(["\'])([^"\']+)\1', line)
                if match:
                    vqd = match.group(2)
                    break

        if not vqd:
            return _fallback_image_search(query, max_results)

        img_url = f"https://duckduckgo.com/i.js?q={requests.utils.quote(query)}&vqd={vqd}&o=json&p=1"
        img_resp = requests.get(img_url, headers=HEADERS, timeout=15)
        img_resp.raise_for_status()
        data = img_resp.json()
        results = [item["image"] for item in data.get("results", [])[:max_results]]
        return results
    except Exception as e:
        return _fallback_image_search(query, max_results)


def _fallback_image_search(query: str, max_results: int = 5) -> list[str]:
    """Fallback: scrape DuckDuckGo HTML for image URLs."""
    try:
        url = "https://html.duckduckgo.com/html/"
        resp = requests.post(url, data={"q": f"{query} image"}, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        urls = []
        for a in soup.select(".result__title a")[:max_results]:
            href = a.get("href", "")
            if href:
                urls.append(href)
        return urls
    except Exception as e:
        return [f"Image search error: {e}"]


def image_download(url: str, filename: str | None = None) -> str:
    """Download an image to workspace/downloads. Returns saved path."""
    _BASE.mkdir(parents=True, exist_ok=True)

    if not filename:
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path) or "image.jpg"

    path = (_BASE / filename).resolve()
    if not str(path).startswith(str(_BASE.resolve())):
        raise PermissionError("Path traversal detected")

    with requests.get(url, headers=HEADERS, stream=True, timeout=30) as resp:
        resp.raise_for_status()
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

    return str(path)
