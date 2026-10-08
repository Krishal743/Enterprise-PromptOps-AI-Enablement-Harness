from __future__ import annotations

from ops_ai.settings import PROMPTS_PATH


def versions() -> list[str]:
    return sorted(path.stem.removeprefix("triage_") for path in PROMPTS_PATH.glob("triage_v*.txt"))


def load_prompt(version: str) -> str:
    if version not in versions():
        raise ValueError(f"Unknown prompt version: {version}")
    return (PROMPTS_PATH / f"triage_{version}.txt").read_text(encoding="utf-8")
