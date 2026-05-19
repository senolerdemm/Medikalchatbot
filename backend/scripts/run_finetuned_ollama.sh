#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
PYTHON_BIN="${PYTHON_BIN:-$BACKEND_DIR/venv/bin/python}"
MODEL_NAME="${LLM_MODEL:-medassist-finetuned}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python virtualenv bulunamadi: $PYTHON_BIN"
  exit 1
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama bulunamadi."
  exit 1
fi

if ! ollama list | awk 'NR > 1 {print $1}' | grep -Eq "^${MODEL_NAME}(:latest)?$"; then
  echo "Ollama modeli bulunamadi: $MODEL_NAME"
  echo "Once calistirin: backend/scripts/create_finetuned_ollama.sh"
  exit 1
fi

export DATABASE_URL="${DATABASE_URL:-sqlite:///$BACKEND_DIR/local_runtime_demo.db}"
export LLM_PROVIDER="ollama"
export LLM_MODEL="$MODEL_NAME"
export LLM_MAX_NEW_TOKENS="${LLM_MAX_NEW_TOKENS:-96}"
export LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-90}"
export LLM_CONTEXT_WINDOW="${LLM_CONTEXT_WINDOW:-2048}"
export LLM_KEEP_ALIVE="${LLM_KEEP_ALIVE:-30m}"
export LLM_TEMPERATURE="${LLM_TEMPERATURE:-0.2}"

echo "MedicalChatbot fine-tuned Ollama modu basliyor."
echo "Backend: http://$HOST:$PORT"
echo "DB: $DATABASE_URL"
echo "LLM: $LLM_MODEL"

cd "$BACKEND_DIR/src"
exec "$PYTHON_BIN" -m uvicorn main:app --host "$HOST" --port "$PORT"
