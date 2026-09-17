# DS RPC 01: Internal Chatbot with Role-Based Access Control

This is a RAG (Retrieval-Augmented Generation) based internal chatbot. Employees authenticate, and their questions are answered using only the internal documents their role is permitted to see. It's built for Codebasics's [Resume Project Challenge](https://codebasics.io/challenge/codebasics-gen-ai-data-science-resume-project-challenge).

![alt text](resources/RPC_01_Thumbnail.jpg)

## How it works

1. **Ingestion** (`scripts/ingest.py`) — walks `resources/data/<department>/`, where each folder name is a department tag. Markdown files are split header-aware then chunked, CSVs are loaded row-per-document (so tabular data like HR records isn't broken mid-row). Every chunk is tagged with `department`, `source`, and `doc_type` metadata, embedded with a `sentence-transformers` model, and stored in a local Qdrant vector database (`resources/qdrant_db/`, collection `company_docs`).
2. **Auth** (`app/main.py`) — FastAPI service using HTTP Basic Auth. Passwords are bcrypt-hashed via `passlib`. Each user has a role (`engineering`, `finance`, `hr`, `marketing`, `general`).
3. **Retrieval + chat** (`/chat` endpoint) — *in progress*. Will embed the user's question, search Qdrant filtered to the departments their role can access, and pass the retrieved chunks to an LLM (via `langchain-groq`) to generate a grounded answer.

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
curl -u Tony:password123 http://127.0.0.1:8000/login
```

## Status

- [x] Basic Auth with hashed passwords and role assignment
- [x] Document ingestion, chunking, embedding, and vector storage
- [ ] Role-filtered retrieval + LLM-generated answers in `/chat`
