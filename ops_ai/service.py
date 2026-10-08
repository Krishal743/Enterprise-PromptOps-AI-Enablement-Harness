from __future__ import annotations

import re
from uuid import uuid4

from ops_ai.prompts import load_prompt
from ops_ai.provider import generate
from ops_ai.retrieval import get_index
from ops_ai.schemas import Evidence, Priority, Team, TicketRequest, TriageDraft, TriageResponse
from ops_ai.storage import TicketStore
from ops_ai.telemetry import observation, redact, trace

BATTERY_HAZARD = re.compile(
    r"\b(smoke|fire|flames?|sparks?|burning smell|hot battery|overheat(?:ing)?)\b", re.IGNORECASE
)
BRAKE_HAZARD = re.compile(
    r"\b(brake|brakes|stopping)\b.{0,35}\b(fail|failed|failure|weak|unresponsive|not working|cannot|can't)\b|\b(cannot|can't) stop\b|\bstop(?:ping)?\b.{0,20}\bnot working\b",
    re.IGNORECASE,
)
RANK = {Priority.routine: 0, Priority.urgent: 1, Priority.critical: 2}


def safety_document(description: str) -> dict | None:
    index = get_index()
    if BATTERY_HAZARD.search(description):
        return index.by_id["KB-BAT-102"]
    if BRAKE_HAZARD.search(description):
        return index.by_id["KB-BRK-401"]
    return None


def safe_fallback(reason: str) -> TriageDraft:
    return TriageDraft(
        category="unclassified",
        priority=Priority.routine,
        recommended_team=Team.human_review,
        diagnostic_summary="The available evidence does not support an automated route.",
        evidence=[],
        customer_reply="Thanks for reporting this. A service specialist will review the details before advising next steps.",
        review_required=True,
        review_reason=reason,
    )


def validate_draft(draft: TriageDraft, documents: list[dict], hazard: dict | None) -> TriageDraft:
    ids = {doc["id"] for doc in documents}
    cited = [doc for doc in documents if doc["id"] in {item.source_id for item in draft.evidence}]
    if any(item.source_id not in ids for item in draft.evidence):
        draft = safe_fallback("The model cited an article that was not retrieved.")
    elif draft.recommended_team != Team.human_review and not cited:
        draft = safe_fallback("The recommended route had no cited evidence.")
    elif draft.recommended_team != Team.human_review and not any(
        doc["team"] == draft.recommended_team.value for doc in cited
    ):
        draft = safe_fallback("The cited evidence did not support the recommended team.")
    elif cited:
        draft.category = cited[0]["title"].lower()
        required = max(
            (Priority(doc["priority"]) for doc in cited), key=lambda priority: RANK[priority]
        )
        if RANK[draft.priority] < RANK[required]:
            draft.priority = required
            draft.review_required = True
            draft.review_reason = "Priority raised to match cited article guidance."

    if hazard is not None:
        draft.priority = Priority.critical
        draft.recommended_team = Team(hazard["team"])
        draft.review_required = True
        draft.review_reason = "Safety-sensitive report requires immediate supervisor review."
        draft.customer_reply = hazard["customer_guidance"]
        draft.diagnostic_summary = hazard["summary"]
        draft.evidence = [
            Evidence(source_id=hazard["id"], reason="Safety rule matched the reported hazard.")
        ]
    if draft.recommended_team == Team.human_review:
        draft.review_required = True
    return draft


def triage(
    ticket: TicketRequest,
    *,
    persist: bool = True,
    documents: list[dict] | None = None,
    system_prompt: str | None = None,
) -> TriageResponse:
    prompt = system_prompt if system_prompt is not None else load_prompt(ticket.prompt_version)
    ticket_id = str(uuid4())
    session_id = ticket.session_id or ticket_id
    with trace(session_id, ticket.prompt_version, ticket.model_dump()) as trace_id:
        with observation(
            "retrieve-knowledge",
            {"description": ticket.description, "code": ticket.diagnostic_code},
            as_type="retriever",
        ) as span:
            docs = (
                documents
                if documents is not None
                else get_index().search(ticket.description, ticket.diagnostic_code)
            )
            hazard = safety_document(ticket.description)
            if hazard is not None:
                docs = [hazard] + [doc for doc in docs if doc["id"] != hazard["id"]]
                docs = docs[:3]
            if span is not None:
                span.update(output=[doc["id"] for doc in docs])
        try:
            draft = generate(ticket, docs, prompt)
            draft = validate_draft(draft, docs, hazard)
        except (ValueError, RuntimeError) as error:
            draft = validate_draft(
                safe_fallback(f"Generation failed: {type(error).__name__}"), docs, hazard
            )
        with observation(
            "validated-recommendation", {"retrieval_ids": [doc["id"] for doc in docs]}
        ) as span:
            if span is not None:
                span.update(output=redact(draft.model_dump(mode="json")))
        response = TriageResponse(
            **draft.model_dump(),
            ticket_id=ticket_id,
            prompt_version=ticket.prompt_version,
            trace_id=trace_id,
            retrieval_ids=[doc["id"] for doc in docs],
        )
        if persist:
            TicketStore().save(
                ticket_id, ticket.model_dump(), response.model_dump(mode="json"), trace_id
            )
        return response
