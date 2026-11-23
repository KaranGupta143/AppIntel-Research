"""Statistics, human-review accuracy, and exports. Everything is computed from saved data only."""
from __future__ import annotations
import json, random
from collections import Counter, defaultdict
import pandas as pd
from . import config
from .models import AppResearch

REVIEW_FIELDS = ["auth_methods", "access", "api_types", "mcp", "buildability"]
REVIEW_COLUMNS = ["app_id", "app_name", "field", "automated_result", "human_result",
                  "verdict", "source_url", "notes", "pass_number"]
VERDICTS = ("Correct", "Incorrect", "Partially correct")


def _flat(value) -> str:
    return "; ".join(value) if isinstance(value, list) else str(value)


# ---------- research statistics ----------
def compute_stats(results: list[AppResearch], total_apps: int, reviews: pd.DataFrame) -> dict:
    n = len(results)
    checked_reviews = checked_rows(reviews)
    stats: dict = {"total_apps": total_apps, "researched": n, "pending": total_apps - n,
                   "manually_verified": int(checked_reviews["app_id"].nunique()) if len(checked_reviews) else 0}
    if n == 0:
        return stats | {"auth": {}, "access": {}, "mcp": {}, "buildability": {}, "blockers": {},
                        "api_types": {}, "evidence": {}, "verified": {"n": 0, "auth": {},
                        "access": {}, "api_types": {}, "mcp": {}, "buildability": {}, "blockers": {}},
                        "by_category": {}, "verified_by_category": {}, "easy_wins": [], "needs_outreach": []}
    stats["auth"] = dict(Counter(a for r in results for a in r.auth_methods))
    stats["access"] = dict(Counter(r.access for r in results))
    stats["api_types"] = dict(Counter(a for r in results for a in r.api_types))
    stats["mcp"] = dict(Counter(r.mcp for r in results))
    stats["buildability"] = dict(Counter(r.buildability for r in results))
    stats["evidence"] = dict(Counter(r.evidence for r in results))
    stats["blockers"] = dict(Counter(r.blocker_type for r in results if r.blocker_type not in ("None",)))

    # "Verified" means the record has the strongest evidence grade. Pending,
    # Unverified and Unknown values are never included in this evidence-only view.
    verified = [r for r in results if r.evidence == "Verified"]
    known_auth = lambda r: [v for v in r.auth_methods if v != "Unknown"]
    known_api = lambda r: [v for v in r.api_types if v != "Unknown"]
    stats["verified"] = {
        "n": len(verified),
        "auth": dict(Counter(v for r in verified for v in known_auth(r))),
        "access": dict(Counter(r.access for r in verified if r.access != "Unknown")),
        "api_types": dict(Counter(v for r in verified for v in known_api(r))),
        "mcp": dict(Counter(r.mcp for r in verified if r.mcp != "Unknown")),
        "buildability": dict(Counter(r.buildability for r in verified if r.buildability != "Unknown")),
        "blockers": dict(Counter(r.blocker_type for r in verified
                                 if r.blocker_type not in ("None", "Unknown"))),
    }
    cat = defaultdict(lambda: {"n": 0, "self_serve": 0, "easy": 0, "mcp": 0})
    for r in results:
        c = cat[r.category]; c["n"] += 1
        c["self_serve"] += r.access == "Self-serve"
        c["easy"] += r.buildability == "Easy"
        c["mcp"] += r.mcp in ("Official", "Community")
    stats["by_category"] = dict(cat)

    verified_cat = defaultdict(lambda: {"n": 0, "auth": {}, "api_types": {},
                                        "mcp": {}, "buildability": {}, "access": {},
                                        "blockers": {}})
    for r in verified:
        c = verified_cat[r.category]
        c["n"] += 1
        c["auth"] = dict(Counter(c["auth"]) + Counter(known_auth(r)))
        c["api_types"] = dict(Counter(c["api_types"]) + Counter(known_api(r)))
        if r.mcp != "Unknown":
            c["mcp"] = dict(Counter(c["mcp"]) + Counter({r.mcp: 1}))
        if r.buildability != "Unknown":
            c["buildability"] = dict(Counter(c["buildability"]) + Counter({r.buildability: 1}))
        if r.access != "Unknown":
            c["access"] = dict(Counter(c["access"]) + Counter({r.access: 1}))
        if r.blocker_type not in ("None", "Unknown"):
            c["blockers"] = dict(Counter(c["blockers"]) + Counter({r.blocker_type: 1}))
    stats["verified_by_category"] = dict(verified_cat)
    stats["easy_wins"] = [r.name for r in results if r.buildability == "Easy" and r.access == "Self-serve"
                          and r.evidence != "Unverified"]
    stats["needs_outreach"] = [r.name for r in results if r.access in ("Contact sales / partner", "Approval required")
                               or r.buildability in ("Difficult", "Not Feasible")]
    return stats


# ---------- human verification ----------
def load_reviews() -> pd.DataFrame:
    if not config.REVIEWS_FILE.exists():
        return pd.DataFrame(columns=REVIEW_COLUMNS)
    try:
        df = pd.read_csv(config.REVIEWS_FILE, dtype=str).fillna("")
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        return pd.DataFrame(columns=REVIEW_COLUMNS)
    return df.reindex(columns=REVIEW_COLUMNS, fill_value="")


def checked_rows(reviews: pd.DataFrame) -> pd.DataFrame:
    """Only rows where a human actually recorded a verdict count."""
    return reviews[reviews["verdict"].isin(VERDICTS)] if len(reviews) else reviews


def review_accuracy(reviews: pd.DataFrame) -> dict:
    done = checked_rows(reviews)
    if done.empty:
        pending = len(reviews) if len(reviews) else 0
        return {"status": "Manual verification pending.",
                "fields_reviewed": 0, "fields_pending": pending,
                "rows": []}
    out: dict = {"status": "ok", "by_pass": {},
                 "fields_reviewed": len(done),
                 "fields_pending": int(len(reviews) - len(done)),
                 "rows": []}
    for row in done.to_dict(orient="records"):
        out["rows"].append({
            "app_name": str(row.get("app_name", "")),
            "field": str(row.get("field", "")),
            "automated_result": str(row.get("automated_result", "")),
            "human_result": str(row.get("human_result", "")),
            "verdict": str(row.get("verdict", "")),
            "source_url": str(row.get("source_url", "")),
            "notes": str(row.get("notes", "")),
            "pass_number": str(row.get("pass_number", "")),
        })
    for p, grp in done.groupby(done["pass_number"].replace("", "1")):
        c = Counter(grp["verdict"])
        n = len(grp)
        by_field = {f: {"checked": len(g), "strict": round(100 * (g["verdict"] == "Correct").mean(), 1)}
                    for f, g in grp.groupby("field")}
        out["by_pass"][str(p)] = {
            "fields_checked": n, "apps_checked": int(grp["app_id"].nunique()),
            "correct": c["Correct"], "partial": c["Partially correct"], "incorrect": c["Incorrect"],
            "strict_accuracy": round(100 * c["Correct"] / n, 1),
            "lenient_accuracy": round(100 * (c["Correct"] + 0.5 * c["Partially correct"]) / n, 1),
            "by_field": by_field}
    return out


def make_review_sample(results: list[AppResearch], n: int, seed: int = 42, pass_number: int = 1) -> pd.DataFrame:
    """Random sample of apps, spread across categories. Human columns are left blank to fill in."""
    rng = random.Random(seed)
    by_cat: dict[str, list[AppResearch]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)
    pool = []
    for items in by_cat.values():
        rng.shuffle(items)
    while len(pool) < min(n, len(results)) and any(by_cat.values()):
        for items in by_cat.values():
            if items and len(pool) < n:
                pool.append(items.pop())
    rows = [{"app_id": r.app_id, "app_name": r.name, "field": f, "automated_result": _flat(getattr(r, f)),
             "human_result": "", "verdict": "", "source_url": "", "notes": "", "pass_number": pass_number}
            for r in pool for f in REVIEW_FIELDS]
    return pd.DataFrame(rows, columns=REVIEW_COLUMNS)


def apply_corrections(results: dict[int, AppResearch], reviews: pd.DataFrame) -> int:
    """Copy human answers into the dataset where the agent was Incorrect. Returns number of fields fixed."""
    list_fields = {"auth_methods", "api_types"}
    fixed = 0
    for _, row in checked_rows(reviews).iterrows():
        if row["verdict"] != "Incorrect" or not row["human_result"]:
            continue
        rec = results.get(int(row["app_id"]))
        if rec is None or row["field"] not in REVIEW_FIELDS:
            continue
        value = [v.strip() for v in row["human_result"].split(";")] if row["field"] in list_fields else row["human_result"].strip()
        data = rec.model_dump(); data[row["field"]] = value
        data["human_corrected_fields"] = sorted(set(rec.human_corrected_fields) | {row["field"]})
        if row["source_url"] and row["source_url"] not in data["sources"]:
            data["sources"].append(row["source_url"])
        results[rec.app_id] = AppResearch(**data)     # re-validates the corrected value
        fixed += 1
    return fixed


# ---------- exports ----------
def export_csv(results: list[AppResearch]) -> None:
    rows = [{**r.model_dump(), **{k: _flat(v) for k, v in r.model_dump().items() if isinstance(v, list)}} for r in results]
    if rows:
        pd.DataFrame(rows).to_csv(config.RESULTS_CSV, index=False)
    else:
        pd.DataFrame(columns=[
            "app_id", "name", "category", "description", "auth_methods", "access",
            "api_types", "api_breadth", "mcp", "mcp_url", "auth_sources",
            "api_sources", "mcp_sources", "buildability", "blocker_type", "blocker",
            "sources", "evidence", "notes", "pass_number", "human_corrected_fields",
            "researched_at",
        ]).to_csv(config.RESULTS_CSV, index=False)


def export_site_data(results: list[AppResearch], total_apps: int) -> dict:
    """Writes site/data.js so the dashboard works by double-clicking index.html (no server needed)."""
    reviews = load_reviews()
    payload = {"stats": compute_stats(results, total_apps, reviews),
               "accuracy": review_accuracy(reviews),
               "apps": [r.model_dump() for r in results],
               "catalogue": json.loads(config.APPS_FILE.read_text(encoding="utf-8"))}
    config.SITE_DIR.mkdir(exist_ok=True)
    config.SITE_DATA_FILE.write_text("window.DATA = " + json.dumps(payload, ensure_ascii=False) + ";", encoding="utf-8")
    return payload
