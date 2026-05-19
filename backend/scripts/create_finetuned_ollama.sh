#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

MODEL_NAME="${MODEL_NAME:-medassist-finetuned}"
MERGED_MODEL_PATH="${LLM_MERGED_MODEL_PATH:-$BACKEND_DIR/model_assets/merged-medassist-llama3-final}"
QUANTIZE_LEVEL="${QUANTIZE_LEVEL:-q4_K_M}"
MIN_FREE_GB="${MIN_FREE_GB:-10}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama bulunamadi."
  exit 1
fi

if [[ ! -f "$MERGED_MODEL_PATH/config.json" ]]; then
  echo "Merged fine-tuned model bulunamadi: $MERGED_MODEL_PATH"
  exit 1
fi

if ! compgen -G "$MERGED_MODEL_PATH/*.safetensors" >/dev/null; then
  echo "Merged model safetensors dosyalari bulunamadi: $MERGED_MODEL_PATH"
  exit 1
fi

free_kb="$(df -Pk "$BACKEND_DIR" | awk 'NR==2 {print $4}')"
free_gb="$((free_kb / 1024 / 1024))"
if (( free_gb < MIN_FREE_GB )); then
  echo "Yetersiz disk alani: ${free_gb}GB bos."
  echo "Quantized Ollama modeli olusturmak icin en az ${MIN_FREE_GB}GB bos alan onerilir."
  echo "Alan actiktan sonra bu scripti tekrar calistirin."
  exit 2
fi

tmp_modelfile="$(mktemp)"
trap 'rm -f "$tmp_modelfile"' EXIT

cat > "$tmp_modelfile" <<EOF
FROM $MERGED_MODEL_PATH
PARAMETER temperature 0.2
PARAMETER num_ctx 4096
EOF

echo "Ollama fine-tuned model olusturuluyor: $MODEL_NAME"
echo "Merged model: $MERGED_MODEL_PATH"
echo "Quantization: $QUANTIZE_LEVEL"
ollama create "$MODEL_NAME" --experimental --quantize "$QUANTIZE_LEVEL" -f "$tmp_modelfile"
ollama list | grep -E "^${MODEL_NAME}(:latest)?[[:space:]]" || true
