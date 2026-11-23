import json, pandas as pd, pytest
from pydantic import ValidationError
from src import analytics
from src.extractor import parse_json, build_prompt
from src.models import App, AppResearch
from src.search import clean_result_url, is_official, page_text, is_homepage_url, looks_like_api_docs
from src.validator import validate_research

APP = App(id=71, name="Notion", category="Productivity", domain_hint="developers.notion.com")
GOOD = {"description": "Workspace", "auth_methods": ["OAuth2", "Bearer token"], "access": "Self-serve",
        "api_types": ["REST"], "api_breadth": "pages, databases", "mcp": "Official", "mcp_url": "",
        "auth_sources": ["https://developers.notion.com/docs"], "api_sources": ["https://developers.notion.com/docs"],
        "mcp_sources": ["https://developers.notion.com/docs"],
        "buildability": "Easy", "blocker_type": "None", "blocker": "None found",
        "sources": ["https://developers.notion.com/docs"], "notes": ""}
URLS = ["https://developers.notion.com/docs", "https://developers.notion.com",
        "https://blog.example.com/x"]


def rec(**kw):
    d = dict(app_id=1, name="A", category="C"); d.update(kw); return AppResearch(**d)


def test_catalogue_has_100_unique_apps():
    apps = json.load(open("data/apps.json"))
    assert len(apps) == 100 and len({a["id"] for a in apps}) == 100
    assert len({a["category"] for a in apps}) == 10


def test_model_rejects_bad_values():
    with pytest.raises(ValidationError): rec(buildability="Super easy")
    with pytest.raises(ValidationError): rec(sources=["not-a-url"])


def test_validator_drops_unfetched_sources():
    raw = dict(GOOD, sources=["https://developers.notion.com/docs", "https://invented.example/fake"])
    r, warns = validate_research(raw, APP, URLS)
    assert r.sources == ["https://developers.notion.com/docs"] and warns


def test_evidence_grading():
    r, _ = validate_research(GOOD, APP, URLS)
    assert r.evidence == "Verified"
    r, _ = validate_research(dict(GOOD, sources=[]), APP, URLS)
    assert r.evidence == "Unverified"
    nonofficial = dict(GOOD,
                       sources=["https://blog.example.com/x"],
                       auth_sources=["https://blog.example.com/x"],
                       api_sources=["https://blog.example.com/x"],
                       mcp_sources=["https://blog.example.com/x"])
    r, _ = validate_research(nonofficial, APP, URLS)
    assert r.evidence == "Partially Verified"       # non-official source only


def test_claim_evidence_is_homepage_and_claim_specific():
    raw = dict(GOOD,
               auth_sources=["https://developers.notion.com"],
               api_sources=["https://developers.notion.com/docs"],
               mcp_sources=["https://developers.notion.com"])
    r, warns = validate_research(raw, APP, URLS)
    assert r.auth_methods == ["Unknown"]
    assert r.api_sources == ["https://developers.notion.com/docs"]
    assert r.mcp == "Unknown"
    assert r.auth_sources == []
    assert r.mcp_sources == []
    assert any("authentication claim" in w for w in warns)


def test_pending_evidence_and_homepage_filter():
    assert rec().evidence == "Pending"
    assert is_homepage_url("https://notion.com")
    assert not is_homepage_url("https://notion.com/docs")
    assert looks_like_api_docs("https://developers.notion.com/reference", "API reference")
    assert not looks_like_api_docs("https://notion.com", "Notion homepage")


def test_consistency_warning():
    r, warns = validate_research(dict(GOOD, access="Contact sales / partner"), APP, URLS)
    assert any("Easy" in w for w in warns)


def test_parse_json_with_fences():
    assert parse_json('Here:\n```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError): parse_json("no json")


def test_search_helpers():
    assert clean_result_url("//duckduckgo.com/l/?uddg=https%3A%2F%2Fa.com%2Fx&rut=1") == "https://a.com/x"
    assert is_official("https://developers.notion.com/x", "developers.notion.com")
    assert is_official("https://docs.stripe.com/api", "stripe.com")
    assert not is_official("https://medium.com/notion", "notion.com")
    assert "hidden" not in page_text("<script>hidden</script><p>shown</p>")


def test_prompt_contains_pages():
    assert "https://x.com" in build_prompt("X", [{"url": "https://x.com", "text": "hello"}])


def test_stats_empty_and_filled():
    s = analytics.compute_stats([], 100, pd.DataFrame(columns=analytics.REVIEW_COLUMNS))
    assert s["researched"] == 0 and s["pending"] == 100
    r1 = rec(auth_methods=["OAuth2"], access="Self-serve", api_types=["REST"], buildability="Easy", evidence="Verified", blocker_type="None")
    r2 = rec(app_id=2, auth_methods=["OAuth2", "API key"], access="Contact sales / partner", api_types=["GraphQL"], buildability="Difficult", evidence="Unverified", blocker_type="Partner / approval gate")
    s = analytics.compute_stats([r1, r2], 100, pd.DataFrame(columns=analytics.REVIEW_COLUMNS))
    assert s["auth"]["OAuth2"] == 2 and s["easy_wins"] == ["A"] and s["blockers"] == {"Partner / approval gate": 1}
    assert s["api_types"] == {"REST": 1, "GraphQL": 1} and s["verified"]["n"] == 1
    assert s["verified"]["auth"] == {"OAuth2": 1}
    assert s["verified"]["blockers"] == {}
    checked = pd.DataFrame([
        dict(app_id="1", app_name="A", field="mcp", automated_result="x",
             human_result="Official", verdict="Correct", source_url="https://a.com/docs",
             notes="", pass_number="1"),
        dict(app_id="2", app_name="B", field="mcp", automated_result="x",
             human_result="", verdict="", source_url="", notes="", pass_number="1"),
    ])
    s = analytics.compute_stats([r1, r2], 100, checked)
    assert s["manually_verified"] == 1


def test_accuracy_only_counts_checked_rows():
    df = pd.DataFrame([
        dict(app_id="1", app_name="A", field="mcp", automated_result="x", human_result="", verdict="", source_url="", notes="", pass_number="1"),
    ])
    assert analytics.review_accuracy(df)["status"] == "Manual verification pending."
    df = pd.DataFrame([
        dict(app_id="1", app_name="A", field="mcp", automated_result="x", human_result="x", verdict="Correct", source_url="", notes="", pass_number="1"),
        dict(app_id="1", app_name="A", field="access", automated_result="x", human_result="y", verdict="Incorrect", source_url="", notes="", pass_number="1"),
        dict(app_id="2", app_name="B", field="mcp", automated_result="x", human_result="", verdict="", source_url="", notes="", pass_number="1"),
    ])
    acc = analytics.review_accuracy(df)["by_pass"]["1"]
    assert acc["fields_checked"] == 2 and acc["strict_accuracy"] == 50.0
    overall = analytics.review_accuracy(df)
    assert overall["fields_reviewed"] == 2
    assert overall["fields_pending"] == 1
    assert overall["rows"][0]["field"] == "mcp"


def test_apply_corrections():
    results = {1: rec(access="Self-serve")}
    df = pd.DataFrame([dict(app_id="1", app_name="A", field="access", automated_result="Self-serve",
                            human_result="Paid plan required", verdict="Incorrect", source_url="https://a.com/p", notes="", pass_number="1")])
    assert analytics.apply_corrections(results, df) == 1
    assert results[1].access == "Paid plan required" and "access" in results[1].human_corrected_fields


def test_partial_correction_does_not_overwrite():
    results = {1: rec(access="Self-serve")}
    df = pd.DataFrame([dict(app_id="1", app_name="A", field="access", automated_result="Self-serve",
                            human_result="Paid plan required", verdict="Partially correct",
                            source_url="https://a.com/p", notes="", pass_number="1")])
    assert analytics.apply_corrections(results, df) == 0
    assert results[1].access == "Self-serve"


def test_review_sample_spread_and_blank_human_columns():
    rs = [rec(app_id=i, category=f"C{i % 3}") for i in range(9)]
    s = analytics.make_review_sample(rs, 3, seed=1)
    assert s["app_id"].nunique() == 3 and (s["verdict"] == "").all()


def test_composio_check_is_optional_when_package_missing(monkeypatch):
    from src.composio_example import check_composio
    real_import = __import__("importlib").import_module

    def missing(name):
        if name == "composio":
            raise ImportError("not installed")
        return real_import(name)

    monkeypatch.setattr("importlib.import_module", missing)
    result = check_composio("", create_mcp=True)
    assert not result.package_installed
    assert not result.api_key_configured
    assert not result.session_created
    assert not result.mcp_endpoint_created


def test_pipeline_end_to_end_with_mocks(tmp_path, monkeypatch):
    """Full run with fake search/LLM: saves incrementally, resumes, and skips a failing app."""
    from src import config, researcher
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "RESULTS_FILE", tmp_path / "r.json")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(researcher, "web_search", lambda q: [{"title": "t", "url": "https://stripe.com/docs/api", "snippet": ""}])
    monkeypatch.setattr(researcher, "fetch_page", lambda u: "x" * 300)
    calls = {"n": 0}

    def fake_extract(name, pages):
        calls["n"] += 1
        if name == "Salesforce":
            raise RuntimeError("LLM down")
        return dict(GOOD, sources=["https://stripe.com/docs/api"])
    monkeypatch.setattr(researcher, "extract", fake_extract)
    researcher.run([1, 81])                                  # Salesforce fails, Stripe succeeds
    saved = researcher.load_results()
    assert list(saved) == [81] and saved[81].sources == ["https://stripe.com/docs/api"]
    researcher.run([1, 81])                                  # resume: Stripe is skipped
    assert calls["n"] == 3
