"""Research one app: search -> fetch -> extract -> validate. Saves after every app."""
from __future__ import annotations
import json, logging, os
from . import config
from . import analytics
from .extractor import extract
from .models import App, AppResearch
from .search import web_search, fetch_page, is_official, looks_like_api_docs, is_homepage_url
from .validator import validate_research

log = logging.getLogger(__name__)


def load_apps() -> list[App]:
    try:
        data = json.loads(config.APPS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not load app catalogue: {exc}") from exc
    if not isinstance(data, list):
        raise RuntimeError("App catalogue JSON root must be a list")
    apps = []
    for row in data:
        try:
            apps.append(App(**row))
        except Exception as exc:
            log.warning("Skipping invalid catalogue row: %s", exc)
    return apps


def load_results() -> dict[int, AppResearch]:
    if not config.RESULTS_FILE.exists():
        return {}
    try:
        rows = json.loads(config.RESULTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.error("Could not read %s: %s", config.RESULTS_FILE, exc)
        return {}
    results: dict[int, AppResearch] = {}
    if not isinstance(rows, list):
        log.error("Could not load results: JSON root is not a list")
        return results
    for row in rows:
        try:
            rec = AppResearch(**row)
            results[rec.app_id] = rec
        except Exception as exc:
            log.warning("Skipping invalid saved result: %s", exc)
    return results


def save_results(results: dict[int, AppResearch]) -> None:
    """Atomic write: write to a temp file, then replace. A crash cannot corrupt saved work."""
    rows = [r.model_dump() for _, r in sorted(results.items())]
    tmp = config.RESULTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, config.RESULTS_FILE)


def export_results(results: dict[int, AppResearch]) -> None:
    """Export the resumable JSON data and a human-readable CSV."""
    save_results(results)
    analytics.export_csv(list(results.values()))


def gather_pages(app: App) -> list[dict]:
    """Three searches (docs, auth/access, MCP). Official-domain pages are fetched first."""
    queries = [f"{app.name} API documentation {app.domain_hint}",
               f"{app.name} API authentication OAuth API key get credentials",
               f"{app.name} MCP server"]
    hits, seen = [], set()
    for q in queries:
        for h in web_search(q):
            url = h["url"]
            if url in seen:
                continue
            if is_homepage_url(url):
                continue
            if not is_official(url, app.domain_hint) and not looks_like_api_docs(url, h.get("title", ""), h.get("snippet", "")):
                continue
            seen.add(url); hits.append(h)
    hits.sort(key=lambda h: not is_official(h["url"], app.domain_hint))
    pages = []
    for h in hits:
        text = fetch_page(h["url"])
        if len(text) > 200:
            pages.append({"url": h["url"], "text": text})
        if len(pages) >= config.MAX_PAGES_PER_APP:
            break
    return pages


def research_app(app: App) -> AppResearch | None:
    pages = gather_pages(app)
    if not pages:
        log.error("%s: no readable pages found", app.name)
        return None
    raw = extract(app.name, pages)
    rec, warns = validate_research(raw, app, [p["url"] for p in pages])
    for w in warns:
        log.warning("%s: %s", app.name, w)
    return rec


def run(app_ids: list[int], force: bool = False) -> None:
    key_available, provider = config.llm_api_key_status()
    if not key_available:
        log.error(
            "Cannot research: %s API key is not configured. "
            "Copy .env.example to .env and set LLM_PROVIDER plus %s API key.",
            provider,
            "OPENAI_API_KEY" if config.LLM_PROVIDER == "openai" else "ANTHROPIC_API_KEY",
        )
        raise RuntimeError("Missing LLM API credentials")
    config.DATA_DIR.mkdir(exist_ok=True)
    apps = {a.id: a for a in load_apps()}
    results = load_results()
    for i in app_ids:
        app = apps.get(i)
        if app is None:
            log.error("unknown app id %s", i); continue
        if i in results and not force:
            log.info("skip %s (already done)", app.name); continue
        try:
            rec = research_app(app)
        except Exception as exc:                      # keep going if one app fails
            log.exception("%s failed: %s", app.name, exc); continue
        if rec:
            results[i] = rec
            save_results(results)                     # incremental save
            log.info("saved %s [%s]", app.name, rec.evidence)
