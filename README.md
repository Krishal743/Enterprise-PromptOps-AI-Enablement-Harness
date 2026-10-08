# Enterprise AI Operations Triage

A portfolio prototype for **fictional EV service requests**. It combines a FastAPI triage workflow, local vector retrieval, optional OpenAI generation, Langfuse tracing, a 50-case golden dataset, Promptfoo pull-request checks, scheduled DeepEval reports, and a Streamlit supervisor playground.

The recommendation is always reviewed before a **simulated** work order is dispatched. No real vehicle diagnostics, customer records, or field-team integrations are included.

## Quick start

Requires Python 3.11+ and Node.js 24 for Promptfoo.

In an internet-enabled workspace, `bash scripts/bootstrap.sh` installs the API, playground, evaluation, and documentation dependencies and runs local checks. The script does not run paid model evaluations; those require your own API credential.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,playground]'
cp .env.example .env
python -m scripts.validate_assets
python -m pytest -q
uvicorn ops_ai.api:app --reload
```

In another terminal:

```bash
source .venv/bin/activate
streamlit run playground.py
```

For a container-hosted demo, copy `.env.example` to `.env` and run `docker compose up --build`. The API and playground are exposed on ports 8000 and 8501. Keep the demo private if you configure live API keys; the prototype has no user authentication.

The application loads local `.env` values at startup, while explicit shell variables take precedence. The default `OPS_LLM_PROVIDER=mock` runs without credentials. It tests API and workflow behavior only; it does not measure prompt quality. To use the live model, set `OPS_LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `OPS_MODEL`. To send traces and feedback to Langfuse, set `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL`.

## API

FastAPI serves interactive API docs at `http://127.0.0.1:8000/docs`.

```bash
curl -X POST http://127.0.0.1:8000/v1/triage \
  -H 'Content-Type: application/json' \
  -d '{"description":"Charging will not start","diagnostic_code":"S-CHG-201"}'
```

The response contains a ticket ID, route, priority, cited article IDs, customer reply, review flag, prompt version, and trace ID when enabled. `POST /v1/compare` runs v1 and v2 without saving work orders. `POST /v1/feedback` records a 1–5 score. `POST /v1/tickets/{ticket_id}/review` records a supervisor decision.

## Evaluation

```bash
python -m scripts.validate_assets
python -m pytest -q
python -m eval.build_promptfoo_cases
OPS_LLM_PROVIDER=openai OPENAI_API_KEY=... npx --yes promptfoo@0.124.0 eval -c promptfooconfig.yaml --no-cache
python -m pip install -e '.[eval]'
OPS_LLM_PROVIDER=openai OPENAI_API_KEY=... python -m eval.deepeval_suite --limit 10
```

The Promptfoo CI job runs on relevant pull requests and fails if a golden assertion fails. The repository needs an `OPENAI_API_KEY` Actions secret for the live job. DeepEval runs weekly or on demand and writes a JSON report. Judge scores supplement the exact routing and safety checks; they are not proof of correctness.

## Documentation

- [Supervisor runbook](docs/runbook.md)
- [Workspace setup and publication](docs/workspace-setup.md)
- [Evaluation guide](docs/evaluation.md)
- [Architecture and decisions](docs/architecture.md)
- [Prompt library](prompts/templates)

`mkdocs.yml` builds these Markdown pages into a documentation site. The `Publish documentation` workflow deploys it to GitHub Pages after the repository is connected to GitHub and Pages is enabled.

## Limits

All knowledge articles and golden cases are synthetic. The local TF-IDF index is suitable for this small, versioned corpus; it is not a production-scale semantic search service. The repo contains no evidence of routing-time reduction or real operator adoption. Those claims require a measured study.
