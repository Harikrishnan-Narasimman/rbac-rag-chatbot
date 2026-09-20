# Internal Chatbot with Role-Based Access Control

This is a RAG (Retrieval-Augmented Generation) based internal chatbot. Employees authenticate, and their questions are answered using only the internal documents their role is permitted to see.

## How it works

1. **Ingestion** (`scripts/ingest.py`) — walks `resources/data/<department>/`, where each folder name is a department tag. Markdown files are split header-aware then chunked, CSVs are loaded row-per-document (so tabular data like HR records isn't broken mid-row). Every chunk is tagged with `department`, `source`, and `doc_type` metadata, embedded with a `sentence-transformers` model, and stored in a local Qdrant vector database (`resources/qdrant_db/`, collection `company_docs`).
2. **Auth** (`app/main.py`) — FastAPI service using HTTP Basic Auth. Passwords are bcrypt-hashed via `passlib`. Each user has a role.
3. **RBAC** (`app/core/rbac.py`) — each role maps to the departments it may search: its own department plus `general`. The `c-level` role is unrestricted.
4. **Retrieval + chat** (`/chat`) — embeds the question, searches Qdrant filtered to the caller's allowed departments, and passes the chunks to `openai/gpt-oss-120b` on Groq, which answers only from that context or refuses.


### Roles Provided
- **engineering**
- **finance**
- **general**
- **hr**
- **marketing**

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Copy `.env.example` to `.env` and fill in your keys (a free Groq key is enough):

```bash
cp .env.example .env
```


## Running the ingestion pipeline

Builds the Qdrant vector store from `resources/data/`:

```bash
python scripts/ingest.py
```

Note: the Qdrant store runs in local on-disk mode (`resources/qdrant_db/`), so only one process can access it at a time. Don't run ingestion and a query script concurrently.

## Running the API

```bash
fastapi dev app/main.py --reload-dir app
```

Scoping `--reload-dir` to `app/` keeps the auto-reloader from watching the Qdrant data directory, which would otherwise trigger restart loops.

Test with:

```bash
curl -u Natasha:hrpass123 -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Aadhya Saxena'"'"'s salary?"}'
```

Or use the interactive docs at http://127.0.0.1:8000/docs (click Authorize first).


## Status

- [x] Basic Auth with hashed passwords and role assignment
- [x] Document ingestion, chunking, embedding, and vector storage
- [x] Role-filtered retrieval + LLM-generated answers in `/chat`
- [ ] PII guardrails and out-of-scope detection
- [ ] JWT auth + React frontend
- [ ] Evaluation (Ragas/LangSmith) and CI gate
- [ ] Azure deployment, CI/CD and cost monitoring
