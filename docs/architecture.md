# Architecture and decisions

The FastAPI service validates requests and creates structured recommendations. A local TF-IDF vector index ranks fictional knowledge articles by symptom language, while diagnostic codes receive an exact-match boost. This avoids a hosted vector service for a 12-article prototype and makes retrieval reproducible in CI. A safety rule inserts the relevant hazard article and forces critical priority even if a model attempts to downgrade it.

The model receives only the ticket and retrieved articles. When retrieval finds no article, the service skips generation and sends the ticket for routine human review; this prevents the model from inventing a priority or policy without evidence. In Ollama mode, its JSON schema limits citation IDs to the retrieved articles, preventing punctuation errors in model-generated IDs. The service still checks cited article IDs, supported team, and priority. If evidence is invalid, it routes to human review. Every persisted ticket starts in `awaiting_review`; a supervisor action alone changes it to `dispatched_simulated` or `returned_for_review` in SQLite. There is no real field-team integration.

Two versioned triage prompts support side-by-side testing. The Streamlit playground uses the API and labels its three local quality checks as structural checks. Promptfoo calls the same service path for the 50-case golden suite. DeepEval provides additional model-judge signals on scheduled runs. Langfuse traces retrieval and generation with a session ID and prompt version; feedback and approval are recorded as scores when credentials are configured.

A separate eight-case red-team set exercises adversarial ticket text through the live Promptfoo path. Its deterministic checks make regressions visible in CI; case-level outputs still need human inspection because phrase checks cannot cover every unsafe paraphrase. The three colleague-facing prompt templates have a small manifest and usage guide, while the application prompts remain versioned text files.

A separate benchmark measures recommendation latency on the 50 golden cases. A separate local study page collects timed manual and AI-assisted decisions from people without creating work orders. Study data is stored in its own SQLite file, keeping real participant feedback distinct from smoke-test scores. See the [measurement protocol](measurement.md) for the design and claim rules.

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
| Mock, Ollama, and optional OpenAI provider modes | Offline development remains possible; Ollama measures prompt behavior without model API charges. | Local generation uses machine resources; mock comparison does not measure prompt quality. |
| Promptfoo on pull requests | All 50 cases receive deterministic checks; one case per category also runs through Ollama and a local judge. | The sampled live gate does not cover every phrasing, and CPU-only jobs may be slow. |
| DeepEval weekly | Separates response relevance, answer grounding, and retrieval recall on a category-balanced sample. | Local judge scores vary; humans still review failure samples. |
| Langfuse sessions and scores | A supervisor's correction can be traced to the prompt, retrieval, model usage, and result. | Local Langfuse has multiple stateful services and needs Docker, storage, and maintenance. |
| Streamlit playground | Keeps the colleague-facing interface in Python and supports side-by-side comparisons quickly. | Less design flexibility than a dedicated frontend. |
| Separate timed operator study | Makes a human baseline and correction feedback measurable without mixing test clicks into operational feedback. | Requires actual participants; small voluntary samples cannot establish general impact. |
| Fictional data | Makes the repo safe to publish as a portfolio example. | The labels and outcomes do not establish real-world performance. |
