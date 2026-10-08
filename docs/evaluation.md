# Evaluation guide

## Golden dataset

`data/golden.json` contains 50 fictional cases: 12 routine, 8 ambiguous, 8 safety-sensitive, 7 missing-evidence, 5 tone, 5 injection, and 5 out-of-scope. Each case states the expected team, priority, source, review flag, and an example acceptable reply. The example reply guides human review; automated checks do not require exact wording. These labels are hypotheses for a prototype, not an Ather policy.

`python -m scripts.validate_assets` checks count, IDs, source references, and exact diagnostic-code retrieval. `python -m eval.build_promptfoo_cases` compiles those records into Promptfoo tests. Unit tests cover retrieval and API behavior. Promptfoo evaluates the live model and the full triage path on pull requests. It applies exact assertions to all cases and a model-graded groundedness rubric to cases with a reference article. Any failed assertion fails that PR job. The report artifact includes case-level reasons.

## What the scores mean

- **Team and priority:** exact checks against reviewed expectations.
- **Evidence:** a cited article must be among the retrieved articles and the expected article must be cited when supplied.
- **Review:** checks whether risky and unclear cases were flagged.
- **Forbidden phrase:** catches a small list of known unsafe claims. It is not a complete safety filter.
- **DeepEval answer relevancy:** checks whether the reply addresses the request.
- **DeepEval faithfulness:** checks whether claims align with retrieved articles; used as the groundedness check.
- **DeepEval contextual recall:** checks whether retrieval supplied the information needed for the expected answer.

DeepEval runs weekly or on demand for evidence-backed cases. Its scores are diagnostic, not an automatic dispatch decision. Review a sample of traces and disagreements by hand.

## Run locally

```bash
python -m scripts.validate_assets
python -m pytest -q
python -m eval.build_promptfoo_cases
OPS_LLM_PROVIDER=openai OPENAI_API_KEY=... npx --yes promptfoo@0.124.0 eval -c promptfooconfig.yaml --no-cache
OPS_LLM_PROVIDER=openai OPENAI_API_KEY=... python -m eval.deepeval_suite --limit 10
```

The `mock` provider is for offline functional testing. It does not measure prompt quality because its response is deterministic and does not read the prompt.

## Reporting results honestly

Record the model, prompt version, dataset revision, run date, number of cases, and number of failures. For timing claims, compare a defined manual routing process and the prototype on the same tickets; report sample size and median times. Do not call this a production deployment or claim real operator adoption without evidence.
