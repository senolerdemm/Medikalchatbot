#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$BACKEND_DIR/.." && pwd)"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
PYTHON_BIN="${PYTHON_BIN:-$BACKEND_DIR/venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python virtualenv bulunamadi: $PYTHON_BIN"
  echo "Once backend venv kurulumunu tamamlayin."
  exit 1
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama bulunamadi. Mac demo icin once Ollama kurulu olmali."
  exit 1
fi

if ! curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
  echo "Ollama servisi calismiyor. Baslatmak icin: brew services start ollama"
  exit 1
fi

export DATABASE_URL="${DATABASE_URL:-sqlite:///$BACKEND_DIR/local_runtime_demo.db}"
export LLM_PROVIDER="${LLM_PROVIDER:-ollama}"
export LLM_MODEL="${LLM_MODEL:-llama3}"
export LLM_MAX_NEW_TOKENS="${LLM_MAX_NEW_TOKENS:-192}"
export LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-60}"
export LLM_CONTEXT_WINDOW="${LLM_CONTEXT_WINDOW:-2048}"
export LLM_KEEP_ALIVE="${LLM_KEEP_ALIVE:-30m}"

echo "MedicalChatbot local demo basliyor."
echo "Backend: http://$HOST:$PORT"
echo "DB: $DATABASE_URL"
echo "LLM: $LLM_PROVIDER / $LLM_MODEL"
echo "RAG config .env dosyasindan okunur; rapor artefactlari degistirilmez."

cd "$BACKEND_DIR/src"
exec "$PYTHON_BIN" -m uvicorn main:app --host "$HOST" --port "$PORT"
