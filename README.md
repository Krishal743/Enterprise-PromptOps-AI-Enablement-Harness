# Enterprise AI Operations Triage

An end-to-end **portfolio prototype for fictional EV service requests**. It helps a service supervisor inspect a ticket, find relevant diagnostic guidance, review an AI-suggested route and customer reply, and approve a **simulated** work order. The same repository includes prompt comparisons, tracing, evaluation gates, a red-team suite, and guides for non-technical colleagues.

**This is a local lab.** Its knowledge articles and test tickets are synthetic. It has no real customer records, vehicle connection, field-team dispatch, or measured operator adoption.

[Read the published guide](https://krishal743.github.io/Enterprise-PromptOps-AI-Enablement-Harness/) · [Try the playground locally](http://127.0.0.1:8501) · [Inspect API docs locally](http://127.0.0.1:8000/docs)

## How a ticket moves through the system

1. A colleague enters a description and, if available, a diagnostic code in the Streamlit playground or FastAPI endpoint.
2. A small local TF-IDF index ranks the 12 fictional knowledge articles by symptoms; an exact diagnostic-code match gets priority. A hazard rule forces specialist review for reports such as battery heat or ineffective brakes.
3. Ollama's local model drafts a structured team, priority, explanation, citations, and customer reply using only the retrieved articles. A mock mode lets the workflow run offline; OpenAI is optional.
4. The service checks the route and citations. Missing or unsupported evidence goes to `human_review`. A saved ticket waits for a supervisor decision; only an approval changes its status to **simulated** dispatch.
5. Langfuse records retrieval and generation traces, latency, token use, prompt version, and feedback when configured. The playground can compare prompt v1 and v2 side by side.

The application uses Python and FastAPI, a local TF-IDF index, SQLite for the simulated queue, Streamlit for the colleague interface, Ollama for local generation, and self-hosted Langfuse for observability. [Architecture and design choices](docs/architecture.md) explains why each component was chosen and where the prototype stops.

## Quality gates and reusable assets

| Asset | What it checks or enables |
|---|---|
| [50-case golden dataset](data/golden.json) | Versioned fictional routine, ambiguous, safety, missing-evidence, tone, injection, and out-of-scope cases with expected routes, priorities, sources, and review decisions. |
| [Dedicated red-team cases](data/redteam.json) | Eight additional synthetic attacks against instruction boundaries, prompt disclosure, unsafe riding advice, unsupported diagnoses, invented policy, private-data insertion, and fabricated dispatch. See the [case-level live result](reports/redteam-2026-10-09.md). |
| [Promptfoo CI gate](.github/workflows/eval.yml) | Runs all 50 golden cases with deterministic mock checks, seven category-balanced live cases, and all eight red-team cases through the live service path on relevant pull requests. A failing check fails the job. |
| [DeepEval review](.github/workflows/deepeval.yml) | Samples evidence-backed cases for answer relevancy, faithfulness, and retrieval recall weekly or on demand. Model-judge scores need human review. |
| [Reusable prompt library](prompts/templates/README.md) | Three parameterized copy-and-adapt templates for structured extraction, clarifying questions, and customer replies, with a [manifest](prompts/templates/manifest.json) listing inputs and review checks. |
| [Supervisor runbook](docs/runbook.md) | Plain-language steps to review a route, report a failure, add a golden case, change a prompt, and read a Langfuse trace. |

The [evaluation guide](docs/evaluation.md) explains what each check means and how to reproduce it. Mock cases validate workflow behavior; live Ollama cases exercise prompt behavior. Neither a passing rubric nor a synthetic expected label proves real-world diagnostic correctness.

## Run locally

For a complete local demo, install Python 3.11+, Node.js 24, Docker Engine with Compose, and ensure `docker info` works without `sudo`. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,playground,eval,docs]'
python -m scripts.prepare_local_stack
export DOCKER_CONFIG="$PWD/.data/docker-config"
mkdir -p "$DOCKER_CONFIG"
docker compose -f compose.yaml -f compose.langfuse.yaml --profile local-ai up -d --build
docker compose -f compose.yaml -f compose.langfuse.yaml --profile local-ai exec ollama ollama pull qwen3:4b
```

Open the [playground](http://127.0.0.1:8501), [API docs](http://127.0.0.1:8000/docs), [Langfuse](http://127.0.0.1:3000), or [timed operator study](http://127.0.0.1:8502). The setup script stores local passwords and Langfuse keys in ignored `.env`; read the initial Langfuse password there and sign in as `operator@example.invalid`. All app ports bind to localhost because the prototype has no user authentication. See the [local stack guide](docs/local-stack.md) for verification and troubleshooting.

To make one fictional request:

```bash
curl -X POST http://127.0.0.1:8000/v1/triage \
  -H 'Content-Type: application/json' \
  -d '{"description":"Charging will not start","diagnostic_code":"S-CHG-201"}'
```

The API also exposes `POST /v1/compare`, `POST /v1/feedback`, and `POST /v1/tickets/{ticket_id}/review`. These let a supervisor compare prompt versions, score an answer, and approve or return a simulated work order.

## Check a change

```bash
python -m scripts.validate_assets
python -m pytest -q
python -m eval.build_redteam_cases
OPS_LLM_PROVIDER=ollama PROMPTFOO_PYTHON=python REQUEST_TIMEOUT_MS=300000 \
  npx --yes promptfoo@0.124.0 eval -c promptfooconfig.redteam.yaml \
  --no-cache --max-concurrency 1 -o eval-results-redteam.json
```

The red-team command needs Ollama and `qwen3:4b` running. Promptfoo also runs automatically in [GitHub Actions](.github/workflows/eval.yml) with no paid model API key. The optional OpenAI provider requires `OPENAI_API_KEY`; the local setup does not. Use the [evaluation guide](docs/evaluation.md) for the full golden suite and DeepEval commands.

## Results and limits

The recorded [50-case routing benchmark](reports/routing-benchmark-2026-10-09.json) had a **9.61-second median** service recommendation time. Team, priority, and review flag matched the synthetic golden labels in 50/50 cases. The separate red-team report records an actual local model run; both are prototype regression evidence, not field validation.

The [operator study](docs/measurement.md) is ready to compare manual and AI-assisted routing on 14 fictional tickets and collect usefulness and correction feedback. **No participants have completed it yet.** This repository therefore does not support a claim of reduced human routing time, real operator adoption, or production safety. Before operational use, the workflow would need approved diagnostic content, authentication, data-handling controls, and real integration testing.
