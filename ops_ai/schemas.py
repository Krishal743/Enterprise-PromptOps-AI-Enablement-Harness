from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Team(str, Enum):
    battery = "battery"
    charging = "charging"
    drivetrain = "drivetrain"
    braking = "braking"
    connectivity = "connectivity"
    general_service = "general_service"
    human_review = "human_review"


class Priority(str, Enum):
    routine = "routine"
    urgent = "urgent"
    critical = "critical"


class TicketRequest(BaseModel):
    description: str = Field(min_length=8, max_length=4000)
    diagnostic_code: str | None = Field(default=None, max_length=30)
    vehicle_model: str | None = Field(default=None, max_length=80)
    session_id: str | None = Field(default=None, max_length=120)
    prompt_version: str = "v1"


class Evidence(BaseModel):
    source_id: str
    reason: str


class TriageDraft(BaseModel):
    category: str
    priority: Priority
    recommended_team: Team
    diagnostic_summary: str
    evidence: list[Evidence]
    customer_reply: str
    review_required: bool
    review_reason: str


class TriageResponse(TriageDraft):
    ticket_id: str
    prompt_version: str
    trace_id: str | None = None
    retrieval_ids: list[str]


class CompareRequest(BaseModel):
    description: str = Field(min_length=8, max_length=4000)
    diagnostic_code: str | None = None
    vehicle_model: str | None = None
    session_id: str | None = None
    versions: list[str] = Field(default_factory=lambda: ["v1", "v2"])


class FeedbackRequest(BaseModel):
    ticket_id: str
    score: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class ApprovalRequest(BaseModel):
    approved: bool
    team: Team | None = None
    note: str = Field(default="", max_length=1000)
