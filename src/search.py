"""Web search and page fetching. Failures return empty results instead of crashing."""
from __future__ import annotations
import hashlib, json, logging, time
from urllib.parse import urlparse, parse_qs, unquote
import requests
from bs4 import BeautifulSoup
from . import config

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (research-bot; take-home project)"}


def _get(url: str, params: dict | None = None, retries: int = 3) -> requests.Response | None:
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
            if resp.status_code == 429:           # rate limited: wait longer each time
                time.sleep(5 * attempt)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning("GET failed (%s/%s) %s: %s", attempt, retries, url, exc)
            time.sleep(2 * attempt)
    return None


def clean_result_url(href: str) -> str:
    """DuckDuckGo wraps links as //duckduckgo.com/l/?uddg=<real url>. Unwrap them."""
    if "uddg=" in href:
        href = unquote(parse_qs(urlparse(href).query).get("uddg", [""])[0])
    return href if href.startswith("http") else ""


def web_search(query: str, max_results: int = 6) -> list[dict]:
    resp = _get("https://html.duckduckgo.com/html/", params={"q": query})
    if resp is None:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for item in soup.select("div.result"):
        link = item.select_one("a.result__a")
        if not link:
            continue
        url = clean_result_url(link.get("href", ""))
        if url:
            snippet = item.select_one(".result__snippet")
            results.append({"title": link.get_text(strip=True), "url": url,
                            "snippet": snippet.get_text(" ", strip=True) if snippet else ""})
        if len(results) >= max_results:
            break
    time.sleep(config.REQUEST_DELAY)
    return results


def is_official(url: str, domain_hint: str) -> bool:
    """True if the URL host matches the app's own domain (e.g. developers.notion.com for notion.com)."""
    if not domain_hint:
        return False
    host = urlparse(url).hostname or ""
    hint = domain_hint.lower().strip().rstrip(".")
    if hint.startswith("www."):
        hint = hint[4:]
    root = ".".join(hint.split(".")[-2:])
    return host == domain_hint.lower() or host.endswith("." + root) or host == root


def is_homepage_url(url: str) -> bool:
    """A bare marketing/company homepage is not API documentation evidence."""
    parsed = urlparse(url)
    path = unquote(parsed.path).strip("/")
    return parsed.scheme in ("http", "https") and not path


def looks_like_api_docs(url: str, title: str = "", snippet: str = "") -> bool:
    """Conservative filename/content filter that rejects bare homepages."""
    if not url or is_homepage_url(url):
        return False
    haystack = f"{url} {title} {snippet}".lower()
    markers = ("api", "developer", "developers", "docs", "documentation", "reference",
               "auth", "oauth", "mcp", "model context protocol", "sdk")
    return any(marker in haystack for marker in markers)


def page_text(html: str, limit: int = config.PAGE_CHAR_LIMIT) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "svg"]):
        tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())[:limit]


def fetch_page(url: str) -> str:
    """Fetch a page as plain text, with a small disk cache so reruns are cheap."""
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = config.CACHE_DIR / (hashlib.md5(url.encode()).hexdigest() + ".json")
    if cache.exists():
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
            text = cached.get("text")
            if isinstance(text, str):
                return text
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Ignoring unreadable cache entry %s: %s", cache, exc)
    resp = _get(url, retries=2)
    if resp is None or "text/html" not in resp.headers.get("content-type", "text/html"):
        return ""
    text = page_text(resp.text)
    try:
        cache.write_text(json.dumps({"url": url, "text": text}), encoding="utf-8")
    except OSError as exc:
        log.warning("Could not write page cache %s: %s", cache, exc)
    time.sleep(config.REQUEST_DELAY)
    return text
