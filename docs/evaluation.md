# Evaluation guide

## Golden dataset

`data/golden.json` contains 50 fictional cases: 12 routine, 8 ambiguous, 8 safety-sensitive, 7 missing-evidence, 5 tone, 5 injection, and 5 out-of-scope. Each case states the expected team, priority, source, review flag, and an example acceptable reply. The example reply guides human review; automated checks do not require exact wording. These labels are hypotheses for a prototype, not an Ather policy.

`python -m scripts.validate_assets` checks count, IDs, source references, and exact diagnostic-code retrieval. `python -m eval.build_promptfoo_cases` compiles those records into Promptfoo tests. Unit tests cover retrieval and API behavior. On pull requests, Promptfoo runs exact assertions on all 50 cases using the mock provider and runs one live Ollama case per category with the full triage path and a groundedness rubric where a reference article exists. This live sample can detect prompt changes; the mock suite alone cannot. Any failed assertion fails the PR job. The report artifact includes case-level reasons. Run the full 50-case live suite locally before a major prompt release.

## What the scores mean

- **Team and priority:** exact checks against reviewed expectations.
- **Evidence:** a cited article must be among the retrieved articles and the expected article must be cited when supplied.
- **Review:** checks whether risky and unclear cases were flagged.
- **Forbidden phrase:** catches a small list of known unsafe claims. It is not a complete safety filter.
- **DeepEval answer relevancy:** checks whether the reply addresses the request.
- **DeepEval faithfulness:** checks whether claims align with retrieved articles; used as the groundedness check.
- **DeepEval contextual recall:** checks whether retrieval supplied the information needed for the expected answer.

DeepEval runs weekly or on demand for a small category-balanced group of evidence-backed cases. Its scores are diagnostic, not an automatic dispatch decision. Review a sample of traces and disagreements by hand.

## Dedicated red-team regression

`data/redteam.json` is a separate, versioned set of eight fictional attack tickets. It covers instruction override, forged system authority, unsafe riding requests, unsupported diagnosis, invented policy, private-data insertion, and fabricated dispatch. `python -m eval.build_redteam_cases` compiles it into Promptfoo tests. A dedicated assertion checks the expected team, priority, review decision, evidence, required safety wording, and attack-specific forbidden content. CI runs **all eight through the live service path**, including model calls where knowledge is available and deterministic human-review fallbacks where it is not. The [dated case-level report](https://github.com/Krishal743/Enterprise-PromptOps-AI-Enablement-Harness/blob/main/reports/redteam-2026-10-09.md) records one local run.

These checks cover the listed attacks and exact phrases. They are not an exhaustive jailbreak or semantic safety evaluation. Add a new fictional case when a human review or a trace reveals a failure, and inspect the full response rather than trusting the pass count alone.

## Run locally

```bash
python -m scripts.validate_assets
python -m pytest -q
python -m eval.build_promptfoo_cases --mode structural
OPS_LLM_PROVIDER=mock npx --yes promptfoo@0.124.0 eval -c promptfooconfig.yaml --no-cache
python -m eval.build_promptfoo_cases
OPS_LLM_PROVIDER=ollama REQUEST_TIMEOUT_MS=300000 npx --yes promptfoo@0.124.0 eval -c promptfooconfig.yaml --no-cache --max-concurrency 1
OPS_LLM_PROVIDER=ollama python -m eval.deepeval_suite --limit 5
python -m eval.build_redteam_cases
OPS_LLM_PROVIDER=ollama PROMPTFOO_PYTHON=python REQUEST_TIMEOUT_MS=300000 \
  npx --yes promptfoo@0.124.0 eval -c promptfooconfig.redteam.yaml \
  --no-cache --max-concurrency 1 -o eval-results-redteam.json
```

The `mock` provider is for offline functional testing. It does not measure prompt quality because its response is deterministic and does not read the prompt.

## Reporting results honestly

Record the model, prompt version, dataset revision, run date, number of cases, and number of failures. For timing claims, compare a defined manual routing process and the prototype on the same tickets; report sample size and median times. Do not call this a production deployment or claim real operator adoption without evidence.
