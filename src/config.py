"""Paths and settings. Reads a simple .env file without extra libraries."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
SITE_DIR = ROOT / "site"
APPS_FILE = DATA_DIR / "apps.json"
RESULTS_FILE = DATA_DIR / "research_results.json"
RESULTS_CSV = DATA_DIR / "research_results.csv"
REVIEWS_FILE = DATA_DIR / "human_reviews.csv"
SITE_DATA_FILE = SITE_DIR / "data.js"


def _load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_env()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY", "")
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY_SECONDS", "1.5"))
PAGE_CHAR_LIMIT = 6000      # text kept per fetched page
MAX_PAGES_PER_APP = 5


def llm_api_key_status() -> tuple[bool, str]:
    """Check for a usable provider/key pair without returning secret values."""
    provider = LLM_PROVIDER
    if provider == "openai":
        return bool(OPENAI_API_KEY), "OpenAI"
    if provider == "anthropic":
        return bool(ANTHROPIC_API_KEY), "Anthropic"
    return False, f"Unknown provider '{provider}'"
