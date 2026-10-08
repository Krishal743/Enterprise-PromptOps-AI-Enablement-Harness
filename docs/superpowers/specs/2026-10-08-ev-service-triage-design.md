# EV service triage and evaluation design

## Objective

Demonstrate an AI enablement workflow for fictional EV service requests: retrieve diagnostic guidance, recommend a route and customer reply, require supervisor approval, and catch prompt regressions before changes ship.

## Scope

Includes FastAPI, local vector retrieval plus exact code matching, optional live LLM, Langfuse traces, SQLite simulated work orders, 50-case golden suite, Promptfoo PR gate, DeepEval scheduled report, Streamlit comparison, prompt templates, and a plain-language runbook. Excludes real customer data, real dispatch, and claims of production adoption.

## Key interfaces

- `POST /v1/triage` creates a recommendation awaiting review.
- `POST /v1/compare` runs two prompt versions without creating work orders.
- `POST /v1/feedback` records a supervisor score.
- `POST /v1/tickets/{id}/review` records approval or rejection; dispatch is simulated.

## Safety and failure behavior

Hazard phrases force critical priority and specialist review. Missing or unsupported evidence routes to human review. Provider errors fall back to review. No customer reply may be treated as approved repair advice. No external field-team action is performed.

## Acceptance criteria

The API handles routine, unknown, and hazard cases; a request cannot dispatch without review; all 50 dataset records pass integrity checks; Promptfoo runs the golden suite on pull requests with credentials; Langfuse receives live traces and feedback when configured; the playground compares prompt versions; and the runbook lets a supervisor report a failed answer without Python changes.
