#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
PYTHON_BIN="${PYTHON_BIN:-$BACKEND_DIR/venv/bin/python}"

BASE_MODEL_PATH="${LLM_BASE_MODEL_PATH:-$BACKEND_DIR/model_assets/Meta-Llama-3-8B-Instruct}"
ADAPTER_PATH="${LLM_ADAPTER_PATH:-$BACKEND_DIR/model_assets/qlora}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python virtualenv bulunamadi: $PYTHON_BIN"
  exit 1
fi

if [[ ! -f "$BASE_MODEL_PATH/config.json" ]]; then
  echo "Base model bulunamadi: $BASE_MODEL_PATH"
  exit 1
fi

if [[ ! -f "$ADAPTER_PATH/adapter_config.json" ]]; then
  echo "QLoRA adapter bulunamadi: $ADAPTER_PATH"
  exit 1
fi

export DATABASE_URL="${DATABASE_URL:-sqlite:///$BACKEND_DIR/local_runtime_demo.db}"
export LLM_PROVIDER="hf_adapter"
export LLM_BASE_MODEL_PATH="$BASE_MODEL_PATH"
export LLM_ADAPTER_PATH="$ADAPTER_PATH"
export LLM_DEVICE="${LLM_DEVICE:-auto}"
export LLM_MAX_NEW_TOKENS="${LLM_MAX_NEW_TOKENS:-96}"
export LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-180}"
export LLM_CONTEXT_WINDOW="${LLM_CONTEXT_WINDOW:-2048}"
export LLM_TEMPERATURE="${LLM_TEMPERATURE:-0.2}"

echo "MedicalChatbot fine-tuned HF adapter modu basliyor."
echo "Backend: http://$HOST:$PORT"
echo "DB: $DATABASE_URL"
echo "Base model: $LLM_BASE_MODEL_PATH"
echo "Adapter: $LLM_ADAPTER_PATH"
echo "Not: Bu mod Mac'te yavas olabilir; model RAM'e yuklenir."

cd "$BACKEND_DIR/src"
exec "$PYTHON_BIN" -m uvicorn main:app --host "$HOST" --port "$PORT"
