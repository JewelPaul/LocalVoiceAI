import re
from typing import Any

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search DuckDuckGo and return a list of results with title/url/snippet."""
    url = "https://html.duckduckgo.com/html/"
    try:
        resp = requests.post(url, data={"q": query}, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return [{"error": f"Search request failed: {e}"}]

    soup = BeautifulSoup(resp.text, "lxml")
    results = []
    for result in soup.select(".result__body")[:max_results]:
        title_tag = result.select_one(".result__title a")
        snippet_tag = result.select_one(".result__snippet")
        link_tag = result.select_one(".result__url")

        title = title_tag.get_text(strip=True) if title_tag else ""
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
        href = title_tag.get("href", "") if title_tag else ""

        # DuckDuckGo wraps URLs — extract real URL from redirect
        if href.startswith("//duckduckgo.com/l/?uddg="):
            from urllib.parse import unquote, parse_qs, urlparse
            qs = parse_qs(urlparse(href).query)
            href = unquote(qs.get("uddg", [href])[0])

        results.append({"title": title, "url": href, "snippet": snippet})

    return results


def scrape_page(url: str) -> str:
    """Fetch a URL and return cleaned plain text."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return f"Error fetching page: {e}"

    soup = BeautifulSoup(resp.text, "lxml")
    # Remove scripts and styles
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Collapse whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def summarize_webpage(url: str) -> str:
    """Fetch and return a summary (first 2000 chars of main text)."""
    text = scrape_page(url)
    if text.startswith("Error"):
        return text
    return text[:2000]
