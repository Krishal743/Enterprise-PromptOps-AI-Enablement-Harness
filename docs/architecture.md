# Architecture and decisions

The FastAPI service validates requests and creates structured recommendations. A local TF-IDF vector index ranks fictional knowledge articles by symptom language, while diagnostic codes receive an exact-match boost. This avoids a hosted vector service for a 12-article prototype and makes retrieval reproducible in CI. A safety rule inserts the relevant hazard article and forces critical priority even if a model attempts to downgrade it.

The model receives only the ticket and retrieved articles. Its structured output is checked for cited article IDs, supported team, and priority. If evidence is absent or invalid, the service routes to human review. Every persisted ticket starts in `awaiting_review`; a supervisor action alone changes it to `dispatched_simulated` or `returned_for_review` in SQLite. There is no real field-team integration.

Two versioned triage prompts support side-by-side testing. The Streamlit playground uses the API and labels its three local quality checks as structural checks. Promptfoo calls the same service path for the 50-case golden suite. DeepEval provides additional model-judge signals on scheduled runs. Langfuse traces retrieval and generation with a session ID and prompt version; feedback and approval are recorded as scores when credentials are configured.

The prototype assumes fictional data. Contact strings are redacted in trace payloads, but the LLM provider receives ticket text in live mode. Real deployment would require an approved data-handling design, stronger authentication, human-reviewed diagnostic content, and integration tests for actual work-order systems.

## Decision record

| Decision | Reason | Tradeoff |
|---|---|---|
| FastAPI and Pydantic contracts | Ticket and result validation makes failures visible before routing and exposes interactive API docs. | Requires Python dependencies even for a small service. |
| Exact code lookup plus local TF-IDF vectors | Codes need exact matching; symptoms need ranked text retrieval. A 12-article corpus does not justify a separate vector database service. | Vocabulary coverage is limited; ambiguous text must fall back to review. |
| Structured model response | Team, priority, evidence, and reply can be validated independently. | A valid schema cannot prove factual correctness. |
| Deterministic safety escalation | The model cannot downgrade reported smoke, heat, or braking concerns. | Broad keyword rules can cause conservative false positives. |
| SQLite work-order queue | Gives a reproducible approval and audit flow without external integrations. | Not a multi-user production queue. |
| Supervisor approval | A person sees the proposed route before any simulated dispatch. | Slower than automatic dispatch, deliberately so for this prototype. |
| Mock and live provider modes | Offline development remains possible; live mode measures actual prompt behavior. | Mock comparison does not measure prompt quality and is labeled as such in the UI. |
| Promptfoo on pull requests | A changed prompt is checked against every golden case before merge. | Live evaluation needs a configured API secret and has model cost. |
| DeepEval weekly | Separates response relevance, answer grounding, and retrieval recall without making every PR pay for a second judge suite. | Judge scores vary; humans still review failure samples. |
| Langfuse sessions and scores | A supervisor's correction can be traced to the prompt, retrieval, model usage, and result. | Requires a Langfuse account or self-hosted instance for live traces. |
| Streamlit playground | Keeps the colleague-facing interface in Python and supports side-by-side comparisons quickly. | Less design flexibility than a dedicated frontend. |
| Fictional data | Makes the repo safe to publish as a portfolio example. | The labels and outcomes do not establish real-world performance. |
