from __future__ import annotations

import json
from types import SimpleNamespace

from dotenv import dotenv_values

from eval.deepeval_suite import select_cases
from ops_ai.provider import _generate_ollama
from ops_ai.schemas import TriageDraft
from scripts.prepare_local_stack import prepare


def test_ollama_receives_schema_and_validates_reply(monkeypatch):
    import ollama

    draft = TriageDraft(
        category="charging",
        priority="routine",
        recommended_team="charging",
        diagnostic_summary="Charging did not start.",
        evidence=[{"source_id": "KB-CHG-201", "reason": "The code matches."}],
        customer_reply="A specialist will review the charging issue.",
        review_required=False,
        review_reason="",
    )
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        def chat(self, **kwargs):
            captured["chat"] = kwargs
            return SimpleNamespace(
                message=SimpleNamespace(content=draft.model_dump_json()),
                prompt_eval_count=120,
                eval_count=35,
            )

    monkeypatch.setattr(ollama, "Client", FakeClient)
    monkeypatch.setenv("OPS_OLLAMA_HOST", "http://127.0.0.1:11434")
    payload = {
        "ticket": "sample",
        "knowledge_articles": [{"id": "KB-CHG-201"}],
    }
    result, usage = _generate_ollama("qwen3:4b", "Follow the articles", payload)
    assert result == draft
    assert usage == {"input": 120, "output": 35}
    assert captured["client"]["host"] == "http://127.0.0.1:11434"
    assert captured["chat"]["format"]["$defs"]["Evidence"]["properties"]["source_id"]["enum"] == [
        "KB-CHG-201"
    ]
    assert captured["chat"]["think"] is False
    assert json.loads(captured["chat"]["messages"][1]["content"]) == payload


def test_ollama_schema_disallows_citations_without_articles(monkeypatch):
    import ollama

    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def chat(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                message=SimpleNamespace(
                    content=TriageDraft(
                        category="unclassified",
                        priority="routine",
                        recommended_team="human_review",
                        diagnostic_summary="No supporting article.",
                        evidence=[],
                        customer_reply="A specialist will review this.",
                        review_required=True,
                        review_reason="No article found.",
                    ).model_dump_json()
                ),
                prompt_eval_count=1,
                eval_count=1,
            )

    monkeypatch.setattr(ollama, "Client", FakeClient)
    _generate_ollama("qwen3:4b", "Follow the articles", {"knowledge_articles": []})
    assert captured["format"]["properties"]["evidence"]["maxItems"] == 0


def test_local_stack_credentials_are_private_and_stable(tmp_path):
    example = tmp_path / "example"
    example.write_text("OPS_LLM_PROVIDER=mock\n")
    env = tmp_path / ".env"
    prepare(env, example)
    first = dotenv_values(env)
    prepare(env, example)
    second = dotenv_values(env)
    assert first == second
    assert first["OPS_LLM_PROVIDER"] == "ollama"
    assert first["LANGFUSE_PUBLIC_KEY"].startswith("pk-lf-")
    assert first["LANGFUSE_SECRET_KEY"].startswith("sk-lf-")
    assert env.stat().st_mode & 0o777 == 0o600


def test_deepeval_selection_covers_categories_first():
    cases = [
        {"vars": {"case_type": category, "expected_source": "KB-1", "case_id": case_id}}
        for category, case_id in (
            ("routine", "r1"),
            ("routine", "r2"),
            ("safety", "s1"),
            ("tone", "t1"),
        )
    ]
    assert [case["case_id"] for case in select_cases(cases, 3)] == ["r1", "s1", "t1"]
