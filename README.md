# Enterprise AI Operations Triage

A portfolio prototype for **fictional EV service requests**. It combines a FastAPI triage workflow, local vector retrieval, Ollama or optional OpenAI generation, Langfuse tracing, a 50-case golden dataset, Promptfoo pull-request checks, scheduled DeepEval reports, and a Streamlit supervisor playground.

[Read the published documentation](https://krishal743.github.io/Enterprise-PromptOps-AI-Enablement-Harness/).

The recommendation is always reviewed before a **simulated** work order is dispatched. No real vehicle diagnostics, customer records, or field-team integrations are included.

## Quick start

Requires Python 3.11+ and Node.js 24 for Promptfoo.

In an internet-enabled workspace, `bash scripts/bootstrap.sh` installs the API, playground, evaluation, and documentation dependencies and runs local checks. Live evaluations use Ollama after you start the local model; no model API key is required.

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

For a zero-key local demo with Ollama and Langfuse, follow the [local stack guide](docs/local-stack.md). The API, playground, model, and Langfuse dashboard bind to localhost. The prototype has no user authentication; keep it local.

The application loads local `.env` values at startup, while explicit shell variables take precedence. The default `OPS_LLM_PROVIDER=mock` runs without credentials. It tests API and workflow behavior only; it does not measure prompt quality. `OPS_LLM_PROVIDER=ollama` uses a local model with no provider key; `OPS_LLM_PROVIDER=openai` remains optional and needs `OPENAI_API_KEY`. Set `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL` to send traces and feedback. The local setup script creates these keys privately.

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
python -m eval.build_promptfoo_cases --mode structural
OPS_LLM_PROVIDER=mock npx --yes promptfoo@0.124.0 eval -c promptfooconfig.yaml --no-cache
python -m eval.build_promptfoo_cases
OPS_LLM_PROVIDER=ollama REQUEST_TIMEOUT_MS=300000 npx --yes promptfoo@0.124.0 eval -c promptfooconfig.yaml --no-cache --max-concurrency 1
python -m pip install -e '.[eval]'
OPS_LLM_PROVIDER=ollama python -m eval.deepeval_suite --limit 5
```

The Promptfoo CI job runs all 50 structural cases and one live Ollama case per category on relevant pull requests. No model API secret is needed. DeepEval runs weekly or on demand against a small category-balanced sample and writes a JSON report. The full 50-case model suite is available locally. Judge scores supplement exact routing and safety checks; they are not proof of correctness.

## Measure routing time and operator feedback

`OPS_LLM_PROVIDER=ollama python -m scripts.benchmark_routing` measures the service recommendation time on all 50 golden tickets after one warm-up. The separate study page at <http://127.0.0.1:8502> times manual and AI-assisted decisions from real participants and collects confidence, usefulness, and corrections. The [measurement guide](docs/measurement.md) shows how to export an aggregate report from Docker without names or comments, and explains the limits on impact claims.

The recorded local run had a **9.61 s median** across 50 fictional tickets; 30 field-team recommendations took **10.18 s median**, and 20 no-evidence cases used a fast human-review fallback. Team, priority, and review flag matched the golden labels in all 50 cases. These are service timings, not measured human time savings.

## Documentation

- [Supervisor runbook](docs/runbook.md)
- [Workspace setup and publication](docs/workspace-setup.md)
- [Local Ollama and Langfuse stack](docs/local-stack.md)
- [Evaluation guide](docs/evaluation.md)
- [Routing-time measurement and operator study](docs/measurement.md)
- [Architecture and decisions](docs/architecture.md)
- [Prompt library](prompts/templates)

`mkdocs.yml` builds these Markdown pages into a documentation site. The `Publish documentation` workflow deploys it to GitHub Pages on changes to `main`.

## Limits

All knowledge articles and golden cases are synthetic. The local TF-IDF index is suitable for this small, versioned corpus; it is not a production-scale semantic search service. The repo contains no evidence of routing-time reduction or real operator adoption. Those claims require a measured study.
