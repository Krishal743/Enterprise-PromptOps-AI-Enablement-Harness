# Local Ollama and Langfuse

This setup runs the fictional EV triage lab on one machine. Ollama serves a local model; Langfuse records traces, token counts, latency, and supervisor feedback. It incurs no model API charges. Your machine supplies the CPU, memory, disk, and electricity.

## Start the stack

Install Docker Engine with the Compose plugin, then check that `docker info` works without `sudo` in the terminal running these commands. From the project root:

```bash
source .venv/bin/activate
python -m scripts.prepare_local_stack
export DOCKER_CONFIG="$PWD/.data/docker-config"
mkdir -p "$DOCKER_CONFIG"
docker compose -f compose.yaml -f compose.langfuse.yaml --profile local-ai up -d --build
docker compose -f compose.yaml -f compose.langfuse.yaml --profile local-ai exec ollama ollama pull qwen3:4b
docker compose -f compose.yaml -f compose.langfuse.yaml --profile local-ai ps
```

The preparation script creates or updates the ignored `.env` file with random local database passwords, a Langfuse project key pair, and an initial login password. Re-running it preserves generated secrets. Read `LANGFUSE_ADMIN_PASSWORD` privately from `.env` and sign in at <http://127.0.0.1:3000> as `operator@example.invalid`. Do not commit or share `.env`.

Open the playground at <http://127.0.0.1:8501>, the timed operator study at <http://127.0.0.1:8502>, and the API documentation at <http://127.0.0.1:8000/docs>. The model listens at <http://127.0.0.1:11434>. All published ports bind to the loopback interface because this prototype does not authenticate API, playground, or study users. See the [measurement protocol](measurement.md) before recruiting participants.

## Verify a full request

1. In the playground, compare prompt versions on a fictional charging request.
2. Save one request, leave a feedback score, and approve or return the simulated work order.
3. In Langfuse, open the `triage-request` trace for that session. Check the retrieval span, `triage-llm` generation, token usage, and feedback score.
4. If a trace is absent, inspect `docker compose -f compose.yaml -f compose.langfuse.yaml --profile local-ai logs langfuse-web langfuse-worker api` and verify `LANGFUSE_BASE_URL`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY` in `.env`.

The local model has no provider bill. Langfuse can still show latency and token usage; a missing or zero currency cost is expected unless you configure your own cost model. Scores from a small local judge need human review.

## Run evaluations

With `.venv` active and the model downloaded:

```bash
python -m eval.build_promptfoo_cases --mode structural
OPS_LLM_PROVIDER=mock npx --yes promptfoo@0.124.0 eval -c promptfooconfig.yaml --no-cache
python -m eval.build_promptfoo_cases
OPS_LLM_PROVIDER=ollama REQUEST_TIMEOUT_MS=300000 npx --yes promptfoo@0.124.0 eval -c promptfooconfig.yaml --no-cache --max-concurrency 1
OPS_LLM_PROVIDER=ollama python -m eval.deepeval_suite --limit 5
```

Promptfoo's full live run makes many model calls and can take time on CPU. Pull-request CI uses one live case per case category plus all 50 structural cases. The scheduled DeepEval report scores a small category-balanced sample.

## Stop and retain data

```bash
docker compose -f compose.yaml -f compose.langfuse.yaml --profile local-ai down
```

This leaves named volumes and model weights in place. Docker Compose is suitable for a portfolio lab; it does not provide backups, high availability, or automatic scaling. See [Langfuse's self-hosting guidance](https://langfuse.com/self-hosting/deployment/docker-compose) before using a similar setup for operational data.
