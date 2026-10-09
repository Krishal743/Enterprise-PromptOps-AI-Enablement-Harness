# Routing-time measurement and operator study

This project separates **automated recommendation latency** from **human routing time**. A fast model call alone cannot establish that supervisors finish tickets faster. The benchmark and study use fictional tickets only.

## Measure automated recommendations

With Ollama running and `.venv` active:

```bash
OPS_LLM_PROVIDER=ollama python -m scripts.benchmark_routing --output .data/routing-benchmark.json
```

The command warms the model once, then times the complete `triage` service path for all 50 golden tickets. It records the median, p95, results by case type, and the number of routes, priorities, and review flags that match the golden labels. It does not include browser or HTTP time, and it does not create work orders. Keep the model and machine otherwise idle for a more comparable run. Record the model, prompt version, machine, and date when sharing a result.

### Recorded local run — 9 October 2026

The [raw 50-case report](https://github.com/Krishal743/Enterprise-PromptOps-AI-Enablement-Harness/blob/main/reports/routing-benchmark-2026-10-09.json) used `qwen3:4b`, prompt `v2`, tracing enabled, and a host reporting 32 logical CPUs. One warm-up call was excluded.

| Group | Cases | Median recommendation time | p95 |
|---|---:|---:|---:|
| All golden cases | 50 | 9.61 s | 11.16 s |
| Field-team recommendations | 30 | 10.18 s | 11.60 s |
| Human-review fallbacks | 20 | 0.8 ms | 1.7 ms |

Team, priority, and review flag each matched the golden label in 50/50 cases. Those exact-label checks do not establish diagnostic correctness or customer safety. The very fast human-review path is a deterministic no-evidence fallback, so the overall median should not be presented as the model's generation speed.

## Collect human decisions

Start the local stack described in [Local Ollama and Langfuse](local-stack.md), then open <http://127.0.0.1:8502>. This study page is bound to localhost and asks for no name, email, or customer data. Have participants use the same machine or a supervised private session; do not expose the unauthenticated page to the public internet.

Ask each participant to:

1. Select their actual role, read the study notice, and start.
2. Complete all 14 fictional cases without leaving the page idle. Seven show an AI suggestion and seven do not. Every case offers the same knowledge reference.
3. Choose the final team, priority, and need for human review. Record confidence, and rate usefulness for AI cases. Add a short comment only if it helps explain a correction.

The study stores the model's generation time separately from the participant's decision time. A page refresh retains the active case and its original clock; a long break will inflate that time and should be noted when interpreting the report. Golden answers stay hidden while the participant works. The app does not dispatch any work order.

Export an aggregate report after participants finish. For the Docker Compose study page, read the study container's persistent database:

```bash
docker compose -f compose.yaml -f compose.langfuse.yaml --profile local-ai exec -T study python -m scripts.study_report --stdout > .data/operator-study-report.json
```

If you run `streamlit run study_playground.py` directly on the host instead, use:

```bash
python -m scripts.study_report --output .data/operator-study-report.json
```

The report contains session counts, self-reported roles, manual and assisted time medians, assisted total time including model generation, routing accuracy, confidence, usefulness, and team corrections. It omits participant IDs and free-text comments. Study data stays in the ignored local SQLite database `.data/operator-study.db` or the named Docker volume. The existing playground's smoke-test feedback is excluded.

## Interpret the result

The two conditions contain different tickets matched by category, and participants can learn during the session. Treat a small sample as a usability check. The database counts sessions, not distinct people, so the study owner must confirm participant uniqueness outside the app. Review timing outliers, case mix, and correction comments before using the exploratory percentage in a presentation. A defensible resume impact statement needs at least five distinct relevant operators and a reviewed comparison; the tool never marks a claim ready automatically. Until people complete the study, operator feedback and manual time savings remain **unmeasured**.
