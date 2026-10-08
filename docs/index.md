# EV Service Triage Lab documentation

This is a fictional operations prototype, not an approved vehicle diagnostic system.

- [Supervisor runbook](runbook.md): test requests, review recommendations, and report failures.
- [Workspace setup](workspace-setup.md): install dependencies and publish the project.
- [Evaluation guide](evaluation.md): golden cases, quality checks, and CI results.
- [Architecture and decisions](architecture.md): how the service works and why each component exists.
- [Design specification](superpowers/specs/2026-10-08-ev-service-triage-design.md): agreed scope and acceptance criteria.

To run locally, install the project with `python -m pip install -e '.[dev,playground]'`, start the API with `uvicorn ops_ai.api:app --reload`, then start the interface with `streamlit run playground.py`.
