"""Create a private, repeatable local Ollama + Langfuse configuration."""

from __future__ import annotations

import secrets
import shutil
from pathlib import Path

from dotenv import dotenv_values, set_key

from ops_ai.settings import ROOT


def prepare(env_path: Path, example_path: Path) -> None:
    if not env_path.exists():
        shutil.copyfile(example_path, env_path)
    existing = dotenv_values(env_path)
    generated = {
        "LANGFUSE_POSTGRES_PASSWORD": secrets.token_hex(24),
        "LANGFUSE_CLICKHOUSE_PASSWORD": secrets.token_hex(24),
        "LANGFUSE_REDIS_PASSWORD": secrets.token_hex(24),
        "LANGFUSE_MINIO_PASSWORD": secrets.token_hex(24),
        "LANGFUSE_SALT": secrets.token_hex(24),
        "LANGFUSE_ENCRYPTION_KEY": secrets.token_hex(32),
        "LANGFUSE_NEXTAUTH_SECRET": secrets.token_hex(32),
        "LANGFUSE_ADMIN_PASSWORD": secrets.token_hex(24),
        "LANGFUSE_PUBLIC_KEY": f"pk-lf-{secrets.token_hex(16)}",
        "LANGFUSE_SECRET_KEY": f"sk-lf-{secrets.token_hex(16)}",
    }
    for key, value in generated.items():
        if not existing.get(key):
            set_key(env_path, key, value, quote_mode="never")
    for key, value in {
        "OPS_LLM_PROVIDER": "ollama",
        "OPS_MODEL": "qwen3:4b",
        "OPS_OLLAMA_HOST": "http://127.0.0.1:11434",
        "LANGFUSE_BASE_URL": "http://127.0.0.1:3000",
        "LANGFUSE_DOCKER_BASE_URL": "http://langfuse-web:3000",
    }.items():
        set_key(env_path, key, value, quote_mode="never")
    env_path.chmod(0o600)


if __name__ == "__main__":
    prepare(ROOT / ".env", ROOT / ".env.example")
    print("Local stack settings are ready in .env (mode 0600). Keep this file private.")
    print("Langfuse login: operator@example.invalid; read LANGFUSE_ADMIN_PASSWORD from .env.")
