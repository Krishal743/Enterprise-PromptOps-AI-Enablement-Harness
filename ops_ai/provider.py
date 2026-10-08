from __future__ import annotations

import json
import os

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
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required when OPS_LLM_PROVIDER=openai")

    from openai import APIError, OpenAI

    model = os.getenv("OPS_MODEL", "gpt-4o-mini")
    payload = {"ticket": ticket.model_dump(exclude={"session_id"}), "knowledge_articles": documents}
    with observation("triage-llm", payload, as_type="generation", model=model) as span:
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
        draft = response.output_parsed
        if span is not None:
            usage = response.usage
            span.update(
                output=redact(draft.model_dump(mode="json")),
                usage_details={"input": usage.input_tokens, "output": usage.output_tokens}
                if usage
                else None,
            )
        return draft
