# Routing-time and operator-feedback measurement

## Purpose

Measure the prototype's own recommendation latency now, and collect a real human baseline before making any claim about time saved or operator adoption. All study tickets and knowledge articles are fictional. Existing smoke-test feedback is excluded from operator results.

## Two distinct measurements

1. **Automated recommendation latency:** A versioned command runs the same `triage` service path on all 50 golden cases, after one unreported warm-up. It uses `persist=False` to avoid simulated work orders, and records wall-clock duration, expected versus actual team, priority, and review flag for every case. The committed report contains model, prompt version, environment, date, per-case results, median, and p95. It is a latency and quality snapshot on one machine, not a manual-workflow comparison.
2. **Human routing study:** A separate local Streamlit page presents 14 fictional cases, two from each golden category. Each participant sees seven cases without an AI suggestion and seven with one. Condition assignments flip within each category and case order is shuffled per session. Both conditions can inspect the same 12-article reference. The page records the participant's final team, priority, review decision, elapsed decision time, confidence, and optional notes. AI cases additionally record generation time and a 1–5 usefulness score. The suggestion appears before the decision clock starts, so decision time and model latency remain distinguishable.

## Data flow and privacy

The study runs as a local Compose service and calls the existing triage function with `persist=False`; no new work orders are created. A separate SQLite database in the existing local data volume stores pseudonymous session IDs, self-reported role, case assignments, response times, choices, and feedback. It does not ask for names or contact details. The operator-facing page never shows golden labels before submission. Study feedback is linked to the Langfuse trace when tracing is configured.

## Reporting and claim rules

The study report lists session count and self-reported role, completion count, manual and assisted decision-time medians, assisted total time including generation, routing accuracy, and usefulness scores. These are descriptive comparisons across matched categories and different cases. A session count cannot prove how many distinct people participated. If there are no human submissions, the report explicitly says human results are pending. A resume percentage is not supported until the study owner confirms at least five distinct relevant operators completed the study and reviews case mix, learning effects, and uncertainty. No feedback, timings, or participants are fabricated.

## Failure behavior and verification

Study progress is stored after each submitted case; page refreshes keep the active case and its original start time. Duplicate submissions do not create extra rows. Model failure is shown as a human-review recommendation and counted in generation time. Tests cover balanced assignment, hidden labels, elapsed-time persistence, duplicate protection, and report calculations. The API, playground, and existing CI behavior remain unaffected by the separate study service.
