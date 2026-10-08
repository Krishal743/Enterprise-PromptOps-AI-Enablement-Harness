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

Copy `.env.example` to `.env` for local settings, or run `python -m scripts.prepare_local_stack` to create private Ollama and Langfuse settings. The mock provider runs without an API key. Ollama is the default live option and needs no model API key. OpenAI remains optional. Keep `.env` private; never commit credentials. See the [local stack guide](local-stack.md).

## Check live evaluations

After bootstrap and Ollama is running with `qwen3:4b` downloaded:

```bash
source .venv/bin/activate
python -m eval.build_promptfoo_cases
OPS_LLM_PROVIDER=ollama npx --yes promptfoo@0.124.0 eval -c promptfooconfig.yaml --no-cache --max-concurrency 1
OPS_LLM_PROVIDER=ollama python -m eval.deepeval_suite --limit 5
```

These checks use local compute. Inspect failures before making a claim about accuracy or regression prevention.

## Publish to GitHub

Authenticate GitHub in an internet-enabled terminal with `gh auth login -h github.com`; check with `gh auth status`. The repository is `https://github.com/Krishal743/Enterprise-PromptOps-AI-Enablement-Harness.git`. If Codex protects the current checkout's `.git` directory, clone the repository into a normal writable checkout before committing. Review the diff and push without forcing. The Ollama Promptfoo and DeepEval workflows require no API secrets. The documentation site uses GitHub Pages with **GitHub Actions** as its publishing source.

After pushing, open the Actions tab and check the AI quality gates, documentation build, and scheduled evaluation workflow. A successful local bootstrap alone does not verify the hosted workflows.
