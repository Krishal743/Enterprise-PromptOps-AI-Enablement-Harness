# Workspace setup and publication

## Prepare the development workspace

Use Python 3.11 or newer and Node.js 24 or newer. In Codex CLI, start a new session with workspace write access, on-request approvals, and command networking enabled:

```bash
codex -C /home/pesu-rf/pes284 --sandbox workspace-write --ask-for-approval on-request -c sandbox_workspace_write.network_access=true
```

The equivalent persistent setting in `~/.codex/config.toml` is:

```toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[sandbox_workspace_write]
network_access = true
```

Use `/status` and `/debug-config` in Codex to inspect the effective sandbox and managed policy. If DNS still fails in a normal terminal outside Codex, fix the machine or network connection first; a Codex flag cannot repair host DNS. Managed policy may prevent overriding network or approval settings.

Run from the repository root:

```bash
bash scripts/bootstrap.sh
```

This creates `.venv`, installs all Python extras, fetches the pinned Promptfoo CLI, validates the dataset, runs unit tests, generates Promptfoo cases, compiles Python modules, and builds the documentation. Re-run the command when dependency requirements change.

Copy `.env.example` to `.env` for local settings. Keep `.env` private. The mock provider runs without an API key. For live prompt evaluation, set `OPS_LLM_PROVIDER=openai` and `OPENAI_API_KEY` in your shell or a private secret store. Add Langfuse keys only when you intend to send traces. Do not commit credentials.

## Check live evaluations

After bootstrap and credentials are ready:

```bash
source .venv/bin/activate
python -m eval.build_promptfoo_cases
OPS_LLM_PROVIDER=openai npx --yes promptfoo@0.124.0 eval -c promptfooconfig.yaml --no-cache
OPS_LLM_PROVIDER=openai python -m eval.deepeval_suite --limit 10
```

These checks make paid model calls. Inspect failures before making a claim about accuracy or regression prevention.

## Publish to GitHub

Authenticate GitHub in an internet-enabled terminal with `gh auth login -h github.com`; check with `gh auth status`. The target repository is `https://github.com/Krishal743/Enterprise-PromptOps-AI-Enablement-Harness.git`. The `.git` directory inside this Codex sandbox is protected and currently empty, so clone the repository into a normal writable checkout and extract `enterprise-promptops-source.tar.gz` into it. Review the diff, commit, and push without forcing. In GitHub repository settings, add `OPENAI_API_KEY` as an Actions secret before expecting the live Promptfoo and DeepEval jobs to pass. Enable GitHub Pages with **GitHub Actions** as the source to publish the Markdown documentation.

After pushing, open the Actions tab and check the AI quality gates, documentation build, and scheduled evaluation workflow. A successful local bootstrap alone does not verify the hosted workflows.
