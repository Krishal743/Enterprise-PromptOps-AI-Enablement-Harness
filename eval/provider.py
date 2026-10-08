"""Promptfoo Python provider; executes the same service path used by the API."""

from __future__ import annotations

import json

from ops_ai.schemas import TicketRequest
from ops_ai.service import triage


def call_api(prompt: str, options: dict, context: dict) -> dict:
    variables = context["vars"]
    ticket = TicketRequest(
        description=variables["description"],
        diagnostic_code=variables.get("diagnostic_code"),
        prompt_version="v2",
        session_id=f"eval-{variables['case_id']}",
    )
    response = triage(ticket, persist=False, system_prompt=prompt)
    return {"output": json.dumps(response.model_dump(mode="json"), ensure_ascii=False)}
