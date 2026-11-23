# AppIntel Integration Research

A small Python pipeline plus a static dashboard. For each of 100 apps it researches how a developer gets API access (auth, self-serve vs gated, API type and breadth, MCP availability) and gives a buildability verdict: could this become an AI-agent toolkit today?

Built for the Composio AI Product Ops Intern take-home.

## Status (read this first)
- **Automated tests:** 17 tests pass.
- **Live pilot:** Not completed. No app research results or human-verification records are included.
- **Catalogue:** The repository contains the 100-app catalogue, but this is not evidence that those apps have been researched.
- **Composio SDK/MCP:** Optional. Live SDK/MCP behavior requires credentials and has not been demonstrated in this repository.
All pending dashboard values are honest empty states, not fake results or accuracy numbers.

## How it works
1. `search.py` runs 3 web searches per app (docs, auth/access, MCP) and fetches up to 5 pages, official domains first.
2. `extractor.py` asks an LLM to fill a fixed JSON shape using **only** the fetched text. Missing facts become `Unknown`.
3. `validator.py` drops any source URL that was not actually fetched, checks allowed values, flags contradictions (e.g. "Easy" but gated), and grades evidence: Verified / Partially Verified / Unverified / Pending.
4. `researcher.py` saves after every app (atomic write), skips finished apps on rerun, and continues if one app fails.
5. `analytics.py` computes statistics, exports CSV and `site/data.js`, and calculates accuracy only from human-checked rows.

## Folder structure
```
data/    apps.json (100 apps) · research_results.json/.csv · human_reviews.csv
src/     config, models, search, extractor, validator, researcher, analytics, main
site/    index.html, style.css, app.js, data.js (generated)
tests/   test_project.py
```

## Setup (Windows)
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
Open `.env` and add ONE key (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`, and set `LLM_PROVIDER`). Never commit `.env`.

## Run
```
python -m src.main pilot                      # 3 apps: Salesforce, Zendesk, GitHub
python -m src.main research --ids 5 12 71     # chosen apps
python -m src.main research --all             # all 100 (resumable; add --force to redo)
python -m src.main build                      # CSV + dashboard data
python -m pytest                              # tests
```
Pilot, selected-ID, and all-app runs are resumable. Apps that are already in
`data/research_results.json` are skipped unless `--force` is used. Each successful
app is saved immediately; at the end of a research command, results are exported
to both `data/research_results.json` and `data/research_results.csv`.

PowerShell setup:
```
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```
Add credentials to `.env` for one provider before researching:
- Anthropic: set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`
- OpenAI: set `LLM_PROVIDER=openai` and `OPENAI_API_KEY`

A Claude/ChatGPT free subscription does not automatically provide API credits.
The pipeline will stop before any searches if no configured provider key is
available. Run it again after adding credentials; completed apps are resumed.

Open `site/index.html` by double-clicking it. No server needed.

## Optional Composio SDK/MCP check

Composio is not required by the research pipeline. To test the current SDK locally:

```
python -m pip install -r requirements-composio.txt
copy .env.example .env
```

Set `COMPOSIO_API_KEY` in `.env`, then run:

```
python -m src.main composio-check
python -m src.main composio-check --mcp
```

The first command verifies package/key availability and attempts to create a real
Composio session. The `--mcp` form additionally requests a hosted MCP endpoint.
No session or MCP endpoint is simulated or counted as working unless the SDK
returns one. A missing package or key exits as an explicit status, not a pipeline
failure. A Composio account/project and toolkit authorization may still be required
for toolkit actions, even when session creation succeeds.

## Human verification
```
python -m src.main review-sample --n 15       # creates data/human_reviews.csv
```
For each row, open the official docs and fill `human_result`, `verdict` (Correct / Incorrect / Partially correct), `source_url`, `notes`. Then:
```
python -m src.main apply-reviews              # copy human fixes into the dataset
python -m src.main build
```
Improve the pipeline, rerun with `--force`, make a second sample with `--pass-number 2`, and the dashboard shows accuracy per round, so you can show real movement from first pass to second.
Accuracy counts only rows with a verdict. Strict = "Correct" only; lenient = "Partially correct" counts half.

## Limitations
- Cannot confirm credentials actually work (no sign-ups made).
- Pricing, approval and partner rules behind logins or sales forms can come back `Unknown`.
- JavaScript-only docs sites may fetch as empty text.
- DuckDuckGo HTML search may rate-limit; swap `web_search()` for another provider if needed.
- Buildability is a rubric-based judgement (see `extractor.RULES`).

## Future improvements
Composio SDK/MCP search/fetch automation, a browser-automation fallback for JS-heavy docs, a second-LLM verification pass and scheduled re-checks.
