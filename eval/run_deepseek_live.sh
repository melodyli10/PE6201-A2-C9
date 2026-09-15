#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
MODEL_ID="deepseek/deepseek-chat"

if [[ ! -f ".env" ]]; then
  echo "Missing .env. Create it from .env.example and add OPENROUTER_API_KEY." >&2
  exit 1
fi

if ! grep -q '^OPENROUTER_API_KEY=sk-or-' .env; then
  echo "OPENROUTER_API_KEY is missing or does not look like an OpenRouter key." >&2
  exit 1
fi

if grep -q '^OPENROUTER_API_KEY=<SECRET>' .env; then
  echo "OPENROUTER_API_KEY still contains a placeholder." >&2
  exit 1
fi

echo "Running unit tests..."
"${PYTHON_BIN}" -m unittest eval.test_harness

echo "Checking D5(b) battery size..."
"${PYTHON_BIN}" -m eval.harness \
  --suite d4 \
  --backend scripted \
  --trial-mode battery \
  --dry-run

echo "Starting paid DeepSeek live battery..."
"${PYTHON_BIN}" -m eval.harness \
  --suite d4 \
  --backend live \
  --trial-mode battery \
  --model "${MODEL_ID}" \
  --prompt-version v2-final \
  --allow-live
