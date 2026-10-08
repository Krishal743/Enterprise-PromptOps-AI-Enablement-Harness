# Supervisor runbook

## Before using the lab

All examples are fictional. Enter no real customer names, phone numbers, addresses, registration numbers, or confidential service notes. The lab makes recommendations for review; only the **Approve simulated dispatch** action changes a ticket's status.

## Test a service request

1. Open the Streamlit playground and describe the issue in the **Service request** box.
2. Enter a diagnostic code if the ticket includes one. Leave it blank if it does not.
3. Select **Compare prompt versions**. Both versions receive the same request and knowledge base.
   If the page says **Offline mock mode**, the two outputs will be identical; ask an engineer to enable the live provider before judging prompt changes.
4. Read the route, priority, reply, and evidence in each column. Open **Evidence and checks** to see the cited article IDs.
5. Treat the displayed check count as a structural check. It does not certify a diagnosis.

## Decide what to do

- **Critical priority:** stop and involve a specialist. Check the reply does not suggest riding or a repair. Add a supervisor note before approving simulated dispatch.
- **Human review route:** request missing details or route manually. Never dispatch to `human_review` as a field team.
- **Cited article seems wrong:** do not approve the route. Record the ticket and expected article.
- **Correct recommendation:** save the request, add feedback, and approve a simulated field team.

## Report a bad answer

1. Save the request and give a 1–5 feedback score with a short explanation.
2. Copy the ticket ID, prompt version, wrong route or claim, and the answer you expected.
3. Add a new fictional case to `data/golden.json` using the same fields as existing cases. Give it a unique `case_id` and describe expected team, priority, source, and review behavior.
4. Run `python -m scripts.validate_assets` and the local tests before opening a pull request.
5. Review the Promptfoo artifact attached to the pull request. A red result lists the failed case and check.

## Change a prompt safely

1. Copy `prompts/triage_v2.txt` to the next version name and change one behavior at a time.
2. Add the version to the playground comparison and evaluation configuration when promoting it.
3. Include one example that motivated the change and one new golden case for the failure it fixes.
4. Run the golden suite. Review both new failures and unexpected changes to customer replies.
5. Ask a supervisor to review safety-sensitive examples before adopting the new prompt.

## Read Langfuse

Open the `triage-request` trace for a ticket ID or session. The retrieval step shows which articles were supplied. The `triage-llm` generation shows model usage and duration when live mode is enabled. Filter by prompt version to compare behavior over time. The `supervisor_feedback` score shows whether the answer helped. A worsening score is a reason to inspect examples, not proof of model drift by itself.

## Common failures

| Symptom | Likely cause | First action |
|---|---|---|
| No evidence | No article matched | Check the code and ask for missing details. |
| Wrong team | Similar symptom matched another article | Add a case and review retrieval terms. |
| Model error | Missing API key or provider failure | Check service logs and provider settings; the request should fall back to review. |
| No Langfuse trace | Tracing keys absent or exporter failed | Check `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and host setting. |
| CI fails | At least one expected behavior changed | Open the evaluation artifact and inspect each failed case. |
