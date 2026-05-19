# New Laptop Setup Notes

This repository contains the application source code, configuration templates,
database migrations, demo seed scripts, mock hospital integration, agent logic,
and Flutter client code.

Large runtime artifacts are intentionally not committed to GitHub.

## Files Included In GitHub

- `backend/src/`: FastAPI backend, agents, services, repositories and adapters.
- `backend/alembic/` and `backend/alembic.ini`: database migrations.
- `backend/scripts/`: seed, smoke test, RAG import/evaluation and LLM helper scripts.
- `backend/.env.example`: environment template.
- `docker-compose.yml`: PostgreSQL service.
- `frontend/`: Flutter mobile application.
- `docs/`: architecture diagrams and setup notes.

## Files Not Included In GitHub

The following files must be copied, downloaded, or regenerated on the target
laptop:

- `backend/model_assets/Meta-Llama-3-8B-Instruct/`
- `backend/model_assets/qlora/`
- `outputs/rag_index/index.faiss`
- `outputs/rag_index/chunks.parquet`
- Ollama model: `medassist-finetuned`
- local `.env`
- local SQLite databases and Chroma cache files
- Python virtual environment and Flutter build outputs

## Required Runtime Artifacts

For the report-aligned demo, the target laptop needs:

1. Base model:
   `Meta-Llama-3-8B-Instruct`
2. QLoRA adapter:
   `adapter_config.json`, `adapter_model.safetensors`, tokenizer files
3. RAG index:
   `index.faiss`
4. RAG chunks:
   `chunks.parquet`
5. Ollama model:
   `medassist-finetuned`

## Install Dependencies

```bash
brew install docker
brew install ollama
brew install flutter
```

```bash
cd /path/to/MedicalChatbot/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

```bash
cd /path/to/MedicalChatbot/frontend
flutter pub get
```

## Database Setup

```bash
cd /path/to/MedicalChatbot
docker compose up -d
```

```bash
cd /path/to/MedicalChatbot/backend
source venv/bin/activate
alembic upgrade head
python scripts/seed_demo_data.py
```

## Environment Setup

```bash
cd /path/to/MedicalChatbot/backend
cp .env.example .env
```

Update these paths in `.env` for the target laptop:

```env
EXTERNAL_RAG_CHUNKS_PATH=/path/to/outputs/rag_index/chunks.parquet
EXTERNAL_RAG_INDEX_PATH=/path/to/outputs/rag_index/index.faiss
LLM_MODEL=medassist-finetuned
```

## Create Or Use Fine-Tuned Ollama Model

If `medassist-finetuned` already exists on the laptop:

```bash
ollama list
```

If it does not exist, place the merged fine-tuned model folder or regenerate it
from the base model and QLoRA adapter, then run:

```bash
cd /path/to/MedicalChatbot
backend/scripts/create_finetuned_ollama.sh
```

## Run Backend

```bash
cd /path/to/MedicalChatbot
brew services start ollama
DATABASE_URL="postgresql+psycopg://medical_user:medical_password@127.0.0.1:5432/medical_chatbot" backend/scripts/run_finetuned_ollama.sh
```

## Run Frontend

```bash
cd /path/to/MedicalChatbot/frontend
flutter run
```

Demo account:

```text
senol@example.com
1234
```
