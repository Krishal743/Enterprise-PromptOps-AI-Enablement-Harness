from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # Asset validation can run before dependencies are installed.
    load_dotenv = None


ROOT = Path(__file__).resolve().parent.parent
if load_dotenv is not None:
    load_dotenv(ROOT / ".env", override=False)
KB_PATH = ROOT / "data" / "knowledge.json"
PROMPTS_PATH = ROOT / "prompts"


def provider_name() -> str:
    value = os.getenv("OPS_LLM_PROVIDER", "mock").lower()
    if value not in {"mock", "openai", "ollama"}:
        raise ValueError("OPS_LLM_PROVIDER must be 'mock', 'openai', or 'ollama'")
    return value


def database_path() -> Path:
    return Path(os.getenv("OPS_DB_PATH", str(ROOT / ".data" / "ops.db")))


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
