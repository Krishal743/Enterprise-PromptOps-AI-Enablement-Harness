from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from ops_ai.settings import tracing_enabled


def redact(value: Any) -> Any:
    if isinstance(value, str):
        value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", value)
        return re.sub(r"(?<!\d)(?:\+\d{1,3}[ -]?)?\d{10}(?!\d)", "[PHONE]", value)
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def langfuse_client():
    if not tracing_enabled():
        return None
    from langfuse import get_client

    return get_client()


@contextmanager
def trace(session_id: str, prompt_version: str, request: dict) -> Iterator[str | None]:
    client = langfuse_client()
    if client is None:
        yield None
        return
    from langfuse import propagate_attributes

    with (
        client.start_as_current_observation(
            name="triage-request", input=redact(request)
        ) as observation,
        propagate_attributes(session_id=session_id, metadata={"prompt_version": prompt_version}),
    ):
        yield client.get_current_trace_id()
        observation.update(output={"completed": True})


@contextmanager
def observation(name: str, input_data: Any, as_type: str = "span", model: str | None = None):
    client = langfuse_client()
    if client is None:
        yield None
        return
    with client.start_as_current_observation(
        name=name, as_type=as_type, input=redact(input_data), model=model
    ) as span:
        yield span


def record_feedback(trace_id: str | None, score: int, comment: str) -> None:
    client = langfuse_client()
    if client is not None and trace_id:
        client.create_score(
            trace_id=trace_id,
            name="supervisor_feedback",
            value=float(score),
            data_type="NUMERIC",
            comment=redact(comment)[:500],
        )


def record_approval(trace_id: str | None, approved: bool, note: str) -> None:
    client = langfuse_client()
    if client is not None and trace_id:
        client.create_score(
            trace_id=trace_id,
            name="route_approved",
            value=float(approved),
            data_type="BOOLEAN",
            comment=redact(note)[:500],
        )
