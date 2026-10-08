#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p .data/cache/pip .data/cache/npm .data/promptfoo
export PIP_CACHE_DIR="$PWD/.data/cache/pip"
export npm_config_cache="$PWD/.data/cache/npm"
export PROMPTFOO_CONFIG_DIR="$PWD/.data/promptfoo"
export PROMPTFOO_DISABLE_TELEMETRY=1

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.11+ is required." >&2
  exit 1
fi
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js 24 and npm are required for Promptfoo." >&2
  exit 1
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required.")
PY
node -e 'if (Number(process.versions.node.split(".")[0]) < 24) process.exit(1)' || {
  echo "Node.js 24+ is required for Promptfoo." >&2
  exit 1
}

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev,playground,eval,docs]'
npx --yes promptfoo@0.124.0 --version

.venv/bin/python -m scripts.validate_assets
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest -q
.venv/bin/python -m eval.build_promptfoo_cases
.venv/bin/python -m compileall -q ops_ai eval playground.py
.venv/bin/mkdocs build --strict

echo "Bootstrap complete. Activate with: source .venv/bin/activate"
echo "Live local evaluations need a running Ollama server with qwen3:4b; no model API key is required."
