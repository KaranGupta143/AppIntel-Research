"""Checks extracted data before it is saved. This is the anti-fabrication layer."""
from __future__ import annotations
from urllib.parse import urldefrag
from .models import AppResearch, App
from .search import is_official, is_homepage_url


def _url(url: object) -> str:
    if not isinstance(url, str):
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return ""
    return urldefrag(url)[0]


def _validated_urls(raw: dict, keys: tuple[str, ...], fetched: set[str],
                    official_app: App | None = None) -> list[str]:
    urls: list[str] = []
    for key in keys:
        value = raw.get(key) or []
        if isinstance(value, str):
            value = [value]
        for claimed in value:
            url = _url(claimed)
            if url and url in fetched:
                if not is_homepage_url(url):
                    urls.append(url)
    return list(dict.fromkeys(urls))


def validate_research(raw: dict, app: App, fetched_urls: list[str]) -> tuple[AppResearch, list[str]]:
    """Build a validated record. Returns (record, warnings). Never trusts model-supplied URLs."""
    warnings: list[str] = []
    raw = dict(raw)

    fetched = {_url(u) for u in fetched_urls if _url(u)}

    # 1. Sources must be pages we actually fetched and not bare homepages.
    claimed = raw.get("sources") or []
    claimed = claimed if isinstance(claimed, list) else [claimed]
    kept = [_url(u) for u in claimed if _url(u) in fetched and not is_homepage_url(_url(u))]
    kept = list(dict.fromkeys(kept))
    if len(kept) < len(claimed):
        warnings.append(f"dropped {len(claimed) - len(kept)} source URL(s) that were not fetched")
    raw["sources"] = kept

    raw["auth_sources"] = _validated_urls(raw, ("auth_sources",), fetched)
    raw["api_sources"] = _validated_urls(raw, ("api_sources",), fetched)
    raw["mcp_sources"] = _validated_urls(raw, ("mcp_sources",), fetched)

    # Claims need claim-specific evidence. Never retain a fact supported only by a homepage.
    if raw["auth_sources"]:
        raw["auth_sources"] = [u for u in raw["auth_sources"] if not is_homepage_url(u)]
    else:
        if raw.get("auth_methods") not in (None, [], ["Unknown"]):
            warnings.append("authentication claim had no matching fetched evidence; set to Unknown")
            raw["auth_methods"] = ["Unknown"]
        raw["access"] = raw.get("access") if raw.get("access") == "Unknown" else (
            raw["access"] if raw["auth_sources"] else "Unknown")

    if not raw["api_sources"]:
        if raw.get("api_types") not in (None, [], ["Unknown"]):
            warnings.append("API availability claim had no matching fetched evidence; set to Unknown")
            raw["api_types"] = ["Unknown"]
        if raw.get("api_breadth") not in (None, "", "Unknown"):
            warnings.append("API breadth had no matching evidence; set to Unknown")
            raw["api_breadth"] = "Unknown"

    if raw.get("mcp") == "Official" and not (
        raw["mcp_sources"] and any(is_official(u, app.domain_hint) for u in raw["mcp_sources"])
    ):
        warnings.append("official MCP claim lacks official fetched evidence; set to Unknown")
        raw["mcp"] = "Unknown"
        raw["mcp_url"] = ""

    # 2. An MCP URL must also have been fetched, otherwise clear it.
    mcp_url = _url(raw.get("mcp_url"))
    if mcp_url and (mcp_url not in fetched or is_homepage_url(mcp_url)):
        warnings.append("mcp_url was not in fetched pages; cleared")
        raw["mcp_url"] = ""
    elif mcp_url:
        raw["mcp_url"] = mcp_url

    rec = AppResearch(app_id=app.id, name=app.name, category=app.category,
                      **{k: v for k, v in raw.items() if k in AppResearch.model_fields
                         and k not in ("app_id", "name", "category", "evidence")})
    rec.evidence = grade_evidence(rec, app)
    warnings += consistency_warnings(rec)
    if warnings:
        rec.notes = (rec.notes + " | " if rec.notes else "") + "; ".join(warnings)
    return rec, warnings


def grade_evidence(rec: AppResearch, app: App) -> str:
    """Verified requires official, claim-specific evidence for each reported key fact."""
    if not rec.sources:
        return "Unverified"
    auth_ok = rec.auth_methods != ["Unknown"] and bool(rec.auth_sources)
    access_ok = rec.access != "Unknown" and bool(rec.auth_sources)
    api_ok = rec.api_types != ["Unknown"] and bool(rec.api_sources)
    mcp_reported = rec.mcp != "Unknown"
    mcp_ok = not mcp_reported or bool(rec.mcp_sources)
    official_claim_sources = (
        rec.auth_sources + rec.api_sources + rec.mcp_sources
    )
    official_ok = any(is_official(u, app.domain_hint) for u in official_claim_sources)
    buildability_ok = rec.buildability != "Unknown"
    key_ok = [auth_ok, access_ok, api_ok, buildability_ok]
    if all(key_ok) and mcp_ok and official_ok:
        return "Verified"
    if any(key_ok) or official_ok:
        return "Partially Verified"
    return "Unverified"


def consistency_warnings(rec: AppResearch) -> list[str]:
    out = []
    if rec.buildability == "Easy" and rec.access not in ("Self-serve", "Unknown"):
        out.append("verdict Easy conflicts with gated access")
    if rec.buildability == "Not Feasible" and rec.api_types not in (["Unknown"], ["SDK/CLI only"]):
        out.append("Not Feasible but a public API type was reported")
    if rec.blocker_type == "None" and rec.buildability in ("Difficult", "Not Feasible"):
        out.append("hard verdict without a blocker")
    return out
