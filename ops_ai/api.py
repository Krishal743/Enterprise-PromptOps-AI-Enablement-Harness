from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException

from ops_ai.prompts import versions
from ops_ai.schemas import (
    ApprovalRequest,
    CompareRequest,
    FeedbackRequest,
    TicketRequest,
    TriageResponse,
)
from ops_ai.service import triage
from ops_ai.settings import provider_name
from ops_ai.storage import TicketStore
from ops_ai.telemetry import record_approval, record_feedback

app = FastAPI(title="Enterprise AI Operations Triage", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "provider": provider_name()}


@app.get("/v1/prompts")
def prompt_versions() -> dict:
    return {"versions": versions()}


@app.post("/v1/triage", response_model=TriageResponse)
def triage_ticket(request: TicketRequest) -> TriageResponse:
    try:
        return triage(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/v1/compare", response_model=list[TriageResponse])
def compare_prompts(request: CompareRequest) -> list[TriageResponse]:
    if len(request.versions) != 2 or len(set(request.versions)) != 2:
        raise HTTPException(status_code=400, detail="Choose two distinct prompt versions")
    session_id = request.session_id or f"compare-{uuid4()}"
    try:
        return [
            triage(
                TicketRequest(
                    description=request.description,
                    diagnostic_code=request.diagnostic_code,
                    vehicle_model=request.vehicle_model,
                    session_id=session_id,
                    prompt_version=version,
                ),
                persist=False,
            )
            for version in request.versions
        ]
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/v1/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict:
    record = TicketStore().get(ticket_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return record


@app.get("/v1/work-orders")
def list_work_orders(team: str | None = None) -> dict:
    return {"items": TicketStore().list_work_orders(team)}


@app.post("/v1/feedback")
def submit_feedback(request: FeedbackRequest) -> dict:
    store = TicketStore()
    record = store.get(request.ticket_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    store.add_feedback(request.ticket_id, request.score, request.comment)
    record_feedback(record["trace_id"], request.score, request.comment)
    return {"saved": True}


@app.post("/v1/tickets/{ticket_id}/review")
def review_ticket(ticket_id: str, request: ApprovalRequest) -> dict:
    store = TicketStore()
    record = store.get(ticket_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    selected = request.team or record["response"]["recommended_team"]
    if request.approved and selected == "human_review":
        raise HTTPException(status_code=400, detail="Choose a field team before dispatch")
    selected_value = selected.value if hasattr(selected, "value") else selected
    if (
        request.approved
        and selected_value != record["response"]["recommended_team"]
        and not request.note.strip()
    ):
        raise HTTPException(
            status_code=400, detail="Changing the recommended team requires a supervisor note"
        )
    if (
        request.approved
        and record["response"]["priority"] == "critical"
        and not request.note.strip()
    ):
        raise HTTPException(
            status_code=400, detail="A critical dispatch requires a supervisor note"
        )
    try:
        updated = store.review(ticket_id, request.approved, str(selected_value), request.note)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    record_approval(record["trace_id"], request.approved, request.note)
    return {"ticket_id": ticket_id, "status": updated["status"], "team": updated["approved_team"]}
