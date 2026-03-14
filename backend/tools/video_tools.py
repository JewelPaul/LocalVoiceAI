import re
from urllib.parse import urlencode, quote

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def video_search(query: str, max_results: int = 5) -> list[dict]:
    """Search for videos via DuckDuckGo. Returns list of {title, url}."""
    results = _ddg_video_search(query, max_results)
    if not results:
        results = _youtube_scrape(query, max_results)
    return results


def _ddg_video_search(query: str, max_results: int) -> list[dict]:
    """Attempt DuckDuckGo video search."""
    try:
        url = "https://html.duckduckgo.com/html/"
        resp = requests.post(
            url,
            data={"q": f"{query} site:youtube.com"},
            headers=HEADERS,
            timeout=15,
        )
        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        for item in soup.select(".result__body")[:max_results]:
            title_tag = item.select_one(".result__title a")
            snippet_tag = item.select_one(".result__snippet")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            results.append({"title": title, "url": href, "snippet": snippet})
        return results
    except Exception:
        return []


def _youtube_scrape(query: str, max_results: int) -> list[dict]:
    """Fallback: scrape YouTube search results page."""
    try:
        search_url = f"https://www.youtube.com/results?search_query={quote(query)}"
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        # Extract video IDs from the response
        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', resp.text)
        seen = []
        for vid in video_ids:
            if vid not in seen:
                seen.append(vid)
            if len(seen) >= max_results:
                break

        # Try to extract titles from ytInitialData
        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"', resp.text)

        results = []
        for i, vid in enumerate(seen):
            title = titles[i] if i < len(titles) else f"Video {i + 1}"
            results.append({
                "title": title,
                "url": f"https://www.youtube.com/watch?v={vid}",
            })
        return results
    except Exception as e:
        return [{"error": f"Video search failed: {e}"}]
