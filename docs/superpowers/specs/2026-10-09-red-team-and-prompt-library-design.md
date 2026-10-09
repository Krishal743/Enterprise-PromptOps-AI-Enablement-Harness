# Red-team regression and prompt-library discoverability

## Goal

Make the existing evaluation and enablement assets legible and reproducible. Keep the 50-case fictional golden dataset as the general regression suite. Add a distinct, versioned adversarial suite and a case-level result from a live local model run. Make the three colleague-facing prompt templates easy to find, fill in, and review.

## Design

- Store fictional adversarial tickets in `data/redteam.json`, separate from `data/golden.json`. Each case names the attack, expected route, priority, review behavior, supporting article, and forbidden reply content. Cover instruction override, prompt disclosure, invented dispatch, unsafe riding advice, unsupported diagnosis, out-of-scope policy, and private-data requests.
- Compile the red-team records into Promptfoo tests with a dedicated assertion function. Run the same `eval/provider.py` and `triage` path as the API. Require exact route and review checks plus attack-specific reply checks. Use live Ollama in CI; a mock-only pass does not demonstrate prompt resistance.
- Save a dated case-level report from an actual local run with model, prompt, case count, pass count, and failures. Document the command and limitations. Keep CI's full report as an artifact.
- Add a small JSON manifest for the Markdown templates and a plain-language usage guide with a filled-in example. Validate that manifest parameters match placeholders in template code blocks. These templates remain copy-and-adapt assets; the application continues to load its versioned triage prompts from text files.
- Rewrite the root README around the ticket flow, quality gates, interfaces, setup, observed results, and limits. Explain that cases and knowledge are fictional, the work order is simulated, and operator time savings are unmeasured.

## Verification

Validate the red-team schema and template manifest locally, run unit tests and formatting, run all adversarial cases through local Ollama with Promptfoo, inspect case-level failures, and run the same live suite in GitHub Actions after publishing. Build the documentation site strictly.
