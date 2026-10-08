from __future__ import annotations

import json
import os

from pydantic import ValidationError

from ops_ai.schemas import Evidence, Priority, Team, TicketRequest, TriageDraft
from ops_ai.telemetry import observation, redact


def mock_draft(ticket: TicketRequest, documents: list[dict]) -> TriageDraft:
    if not documents:
        return TriageDraft(
            category="unclassified",
            priority=Priority.routine,
            recommended_team=Team.human_review,
            diagnostic_summary="The available articles do not support a route.",
            evidence=[],
            customer_reply="Thanks for reporting this. Please share any warning code and when the issue began so our team can review it.",
            review_required=True,
            review_reason="No relevant knowledge article was found.",
        )
    doc = documents[0]
    return TriageDraft(
        category=doc["title"].lower(),
        priority=Priority(doc["priority"]),
        recommended_team=Team(doc["team"]),
        diagnostic_summary=doc["summary"],
        evidence=[Evidence(source_id=doc["id"], reason="Matched the reported code or symptoms.")],
        customer_reply=doc["customer_guidance"],
        review_required=doc["review_required"],
        review_reason="Specialist review required by source guidance."
        if doc["review_required"]
        else "",
    )


def generate(ticket: TicketRequest, documents: list[dict], system_prompt: str) -> TriageDraft:
    from ops_ai.settings import provider_name

    if provider_name() == "mock":
        return mock_draft(ticket, documents)
    provider = provider_name()
    model = os.getenv("OPS_MODEL") or ("qwen3:4b" if provider == "ollama" else "gpt-4o-mini")
    payload = {"ticket": ticket.model_dump(exclude={"session_id"}), "knowledge_articles": documents}
    with observation("triage-llm", payload, as_type="generation", model=model) as span:
        if provider == "ollama":
            draft, usage = _generate_ollama(model, system_prompt, payload)
        else:
            draft, usage = _generate_openai(model, system_prompt, payload)
        if span is not None:
            span.update(
                output=redact(draft.model_dump(mode="json")),
                usage_details=usage,
            )
        return draft


def _generate_ollama(model: str, system_prompt: str, payload: dict) -> tuple[TriageDraft, dict]:
    import httpx
    from ollama import Client, ResponseError

    host = os.getenv("OPS_OLLAMA_HOST", "http://127.0.0.1:11434")
    schema = TriageDraft.model_json_schema()
    source_ids = [article["id"] for article in payload.get("knowledge_articles", [])]
    if source_ids:
        schema["$defs"]["Evidence"]["properties"]["source_id"]["enum"] = source_ids
    else:
        schema["properties"]["evidence"]["maxItems"] = 0
    try:
        response = Client(host=host, timeout=float(os.getenv("OPS_OLLAMA_TIMEOUT", "300"))).chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            think=False,
            format=schema,
            options={"temperature": 0, "num_predict": 768},
        )
        draft = TriageDraft.model_validate_json(response.message.content or "")
    except (httpx.HTTPError, ResponseError, ValidationError) as error:
        raise RuntimeError(
            "Local model unavailable or returned invalid structured output"
        ) from error
    return draft, {"input": response.prompt_eval_count or 0, "output": response.eval_count or 0}


def _generate_openai(model: str, system_prompt: str, payload: dict) -> tuple[TriageDraft, dict]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required when OPS_LLM_PROVIDER=openai")
    from openai import APIError, OpenAI

    try:
        response = OpenAI().responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            text_format=TriageDraft,
        )
    except APIError as error:
        raise RuntimeError("Model provider unavailable") from error
    if response.output_parsed is None:
        raise ValueError("Model returned no structured triage response")
    usage = response.usage
    return response.output_parsed, (
        {"input": usage.input_tokens, "output": usage.output_tokens} if usage else {}
    )
