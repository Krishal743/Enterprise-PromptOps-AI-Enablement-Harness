#!/usr/bin/env bash
set -euo pipefail

ollama_version=0.40.1
ollama_dir="${RUNNER_TEMP:?GitHub runner temporary directory is required}/ollama"
mkdir -p "$ollama_dir"
if ! command -v zstd >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y zstd
fi

# Extract only the CPU backend. The official archive also bundles GPU libraries,
# which consume most of a standard GitHub runner's disk without helping CPU jobs.
curl -fsSL --retry 3 \
  "https://github.com/ollama/ollama/releases/download/v${ollama_version}/ollama-linux-amd64.tar.zst" \
  | zstd -d \
  | tar -x -C "$ollama_dir" --exclude='lib/ollama/cuda_v*' --exclude='lib/ollama/vulkan*'

echo "$ollama_dir/bin" >> "${GITHUB_PATH:?GitHub Actions path file is required}"
OLLAMA_MODELS="$RUNNER_TEMP/ollama-models" OLLAMA_HOST=127.0.0.1:11434 \
  nohup "$ollama_dir/bin/ollama" serve > "$RUNNER_TEMP/ollama.log" 2>&1 &

for attempt in {1..60}; do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then
    break
  fi
  if (( attempt == 60 )); then
    cat "$RUNNER_TEMP/ollama.log"
    exit 1
  fi
  sleep 1
done
"$ollama_dir/bin/ollama" pull qwen3:4b > "$RUNNER_TEMP/ollama-pull.log" 2>&1 || {
  cat "$RUNNER_TEMP/ollama-pull.log"
  exit 1
}
echo "Ollama qwen3:4b is ready."
