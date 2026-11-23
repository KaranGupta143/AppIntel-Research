"""Turns fetched page text into structured findings using an LLM. The model may only use the text given."""
from __future__ import annotations
import json, logging, re
import requests
from . import config
from .schemas import EXTRACTION_SCHEMA

log = logging.getLogger(__name__)

SYSTEM = """You are a careful API-integration researcher. Use ONLY the evidence pages provided.
Prefer official developer documentation. A company homepage is not API documentation.
If a fact is not stated in the pages, answer "Unknown". Never guess endpoints, auth or MCP availability.
For authentication, API availability and MCP availability, return the exact evidence page URLs that support each claim.
Do not infer MCP availability from a homepage or from a generic GitHub repository.
Return ONLY one JSON object, no markdown."""

RULES = """Buildability: Easy = documented public API + self-serve credentials. Medium = documented API but extra steps
(app review, paid plan, narrow API). Difficult = partner/contact-sales gate or very limited API. Not Feasible = no public API."""


def build_prompt(app_name: str, pages: list[dict]) -> str:
    blocks = "\n\n".join(f"[PAGE {i+1}] {p['url']}\n{p['text']}" for i, p in enumerate(pages))
    return f"App: {app_name}\n\n{RULES}\n\nJSON shape:\n{EXTRACTION_SCHEMA}\n\nEvidence pages:\n{blocks}"


def parse_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply (handles ```json fences)."""
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in reply")
    try:
        value = json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("model reply contained malformed JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("model reply must be a JSON object")
    return value


def _call_llm(prompt: str) -> str:
    if config.LLM_PROVIDER == "openai":
        r = requests.post("https://api.openai.com/v1/chat/completions", timeout=90,
                          headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                          json={"model": config.OPENAI_MODEL, "temperature": 0,
                                "messages": [{"role": "system", "content": SYSTEM},
                                             {"role": "user", "content": prompt}]})
        r.raise_for_status()
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenAI returned an unexpected response") from exc
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=90,
                      headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
                      json={"model": config.ANTHROPIC_MODEL, "max_tokens": 1200, "temperature": 0,
                            "system": SYSTEM, "messages": [{"role": "user", "content": prompt}]})
    r.raise_for_status()
    data = r.json()
    try:
        return data["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Anthropic returned an unexpected response") from exc


def extract(app_name: str, pages: list[dict]) -> dict:
    """Return the model's raw dict. Raises on API/parse errors so the caller can log and continue."""
    key = config.OPENAI_API_KEY if config.LLM_PROVIDER == "openai" else config.ANTHROPIC_API_KEY
    if not key:
        raise RuntimeError("No LLM API key set. Copy .env.example to .env and add one.")
    return parse_json(_call_llm(build_prompt(app_name, pages)))
