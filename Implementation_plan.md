# RBAC RAG Chatbot — Phased Implementation Plan

## Context

This repo (`rbac-rag-chatbot`) is a fork of the codebasics `ds-rpc-01` course starter, being turned into a portfolio-grade internal RAG chatbot for a fictional AI consultancy (AtliQ). The brief requires: RBAC-gated retrieval, PII/guardrails, Azure deployment with automated eval-gated CI/CD, and cost monitoring.

**What's already built and working:**
- `app/main.py` — FastAPI + HTTP Basic Auth, bcrypt-hashed in-memory `users_db` (7 users across engineering/marketing/finance/hr/general roles). `/chat` is a stub (`return "Implement this endpoint."`).
- `scripts/ingest.py` — fully working ingestion: markdown (header-split + chunked) and CSV loaders, tags each chunk with `department`/`source`/`doc_type`, embeds with `sentence-transformers/all-MiniLM-L6-v2`, stores in local on-disk Qdrant (`resources/qdrant_db/`, collection `company_docs`). Already run — vector store is populated for engineering, finance, hr, general, marketing.
- `pyproject.toml` has langchain, langchain-groq, langchain-qdrant, qdrant-client, sentence-transformers, python-jose, passlib — but several (langchain-groq, python-jose) are unused so far.
- Nothing else exists: no retrieval/RBAC-filter/LLM code, no guardrails, no frontend, no eval/monitoring, no cost tracking, no deployment artifacts (no Dockerfile, no CI/CD, no `.env`).

**User decisions locked in:**
- Frontend: **React** (Vite), calling the FastAPI backend.
- RBAC model: each role sees **its own department + general**; new **`c-level`** role sees everything (no filter).
- Guardrails: **Microsoft Presidio** for PII detection/redaction.
- Cloud: **Azure Container Apps**.

The goal is to finish the unimplemented `/chat` endpoint with real RBAC-filtered retrieval + generation, layer in guardrails, build the React frontend with JWT auth, wire up Ragas/LangSmith eval that gates deploys, add lightweight cost tracking, and ship it all to Azure via containers + GitHub Actions.

## Phase 1 — Core RAG + RBAC chat (local only)

Make `/chat` actually work end-to-end with role-based filtering. No guardrails, frontend, eval, or deploy yet.

- `app/core/config.py` — pydantic-settings `Settings` class (Groq API key, Qdrant path/collection, embedding model name, JWT secret placeholder for later). Add `.env.example`.
- `app/core/rbac.py` — `ROLE_DEPARTMENT_MAP` dict (own dept + `general`; `c-level` → `"*"`/no filter) and `get_allowed_departments(role)`.
- `app/services/vectorstore.py` — load `HuggingFaceEmbeddings` + `QdrantVectorStore.from_existing_collection(...)` once (FastAPI lifespan/module-level singleton, not per-request).
- `app/services/retrieval.py` — builds a `qdrant_client.models.Filter` from allowed departments. **First verify the actual payload key** langchain-qdrant used when ingesting (likely `metadata.department`, not `department`) by inspecting the existing collection — get this wrong and RBAC filtering silently breaks.
- `app/services/rag.py` — retrieval → prompt (`ChatPromptTemplate`, system prompt instructs "answer only from context, refuse if insufficient, cite sources") → `ChatGroq(model="openai/gpt-oss-120b")` via a simple `prompt | llm | StrOutputParser()` LCEL chain.
- `app/schemas/chat.py` — `ChatRequest`/`ChatResponse` (`answer`, `sources`, `department_scope`).
- Modify `app/main.py` — rewire `/chat` to `Depends(authenticate)` + `rag_service.answer(...)`; add a `c-level` test user to `users_db`.
- Fix `scripts/ingest.py` — switch `langchain_community.embeddings.HuggingFaceEmbeddings` → `langchain_huggingface.HuggingFaceEmbeddings` (add dep), drop unused `QdrantClient`/`VectorParams`/`Distance` imports.

**Verify:** hr user's query returns hr+general content only; engineering user asking about financial data gets a refusal/empty result; c-level sees across all departments. Test via the existing curl pattern in the README.

## Phase 2 — Guardrails

- `app/services/guardrails.py` using `presidio-analyzer` + `presidio-anonymizer` (new deps).
  - Input: scan+redact PII in the user's query before it's used in logging/tracing (not a hard block — RBAC, not query content, gates access).
  - Output: scan+redact the generated answer before returning it; tunable entity allowlist in config (permissive on PERSON, strict on SSN/credit card/email) so legitimate HR/finance answers aren't gutted.
  - Out-of-scope detection: `similarity_search_with_score`, skip the LLM call and return a canned refusal if the top score is below a configured threshold — cheaper and simpler than a separate classifier call, and saves cost.
- Modify `app/services/rag.py` to insert this pipeline: redact query → RBAC-filtered scored search → threshold check → generate → redact answer → return.

## Phase 3 — Auth hardening + React frontend

- Move off HTTP Basic to JWT (`python-jose`, already a dep but unused): `app/core/security.py` (`create_access_token`, HS256), `app/routers/auth.py` (`POST /auth/login` via `OAuth2PasswordRequestForm`), `OAuth2PasswordBearer` + `get_current_user` dependency replacing `authenticate()`. Short-lived tokens (30-60 min), no refresh-token flow needed.
- Add `CORSMiddleware` to `app/main.py` with configurable allowed origins.
- New `frontend/` (Vite + React, sibling to `app/`, not nested in the Python package):
  - `src/pages/Login.tsx` — posts to `/auth/login`, stores JWT + role in `sessionStorage`.
  - `src/pages/Chat.tsx` — message list + input, calls `POST /chat` with bearer token, renders answer + sources.
  - `src/api/client.ts` — fetch wrapper, attaches token, redirects to login on 401.

Do this after Phase 2 so the frontend is built against a stable API response contract (including refusal/guardrail behavior), not a moving target.

## Phase 4 — Evaluation & monitoring

- `resources/eval/golden_dataset.jsonl` — hand-curated (LLM-drafted, human-reviewed) Q&A pairs per department, **including RBAC negative cases** (e.g. an engineering-role question about CFO salary → expected refusal, scored separately from Ragas metrics since those assume answerable questions).
- `resources/eval/thresholds.yaml` — minimum acceptable scores.
- `scripts/run_eval.py` — runs Ragas (`faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`) against the golden set plus the custom RBAC-refusal check.
- LangSmith tracing: `LANGCHAIN_TRACING_V2`/`LANGCHAIN_API_KEY`/`LANGCHAIN_PROJECT` env vars in `app/core/config.py` — auto-traces the existing LCEL chains with no code changes.
- `.github/workflows/eval.yml` — runs on PRs touching `app/services/` or `resources/data/`; fails if any metric drops below threshold. This becomes the required check that gates Phase 6's deploy workflow.

## Phase 5 — Containerize + deploy to Azure

- `Dockerfile` (repo root, API) — multi-stage, `python:3.12-slim`, `pip install .`, bakes in `resources/qdrant_db/` (small enough at 1.5MB to ship in-image; document that a growing corpus should migrate to a hosted Qdrant instead).
- `frontend/Dockerfile` — multi-stage Vite build → `nginx:alpine` serving `dist/`, `nginx.conf` reverse-proxying `/api/*` to the backend's Container App FQDN (keeps browser same-origin).
- `docker-compose.yml` + `.dockerignore` for local parity testing before pushing to Azure.
- Manual first deploy: one Azure Container Apps Environment with two apps (`rbac-rag-api`, `rbac-rag-frontend`), both externally ingress-enabled for simplicity. Secrets (`GROQ_API_KEY`, `JWT_SECRET_KEY`, `LANGCHAIN_API_KEY`) via Container Apps' built-in secrets — explicitly skip Azure Key Vault as unneeded complexity for this project's scale.

**Verify:** app reachable at the Container Apps public URL, full RBAC flow working end-to-end in the deployed environment.

## Phase 6 — CI/CD + cost monitoring

- `.github/workflows/deploy.yml` — on push to `main`, gated on `eval.yml` passing; builds/pushes both images to Azure Container Registry and updates both Container Apps. Use GitHub OIDC federated credentials for Azure auth (no long-lived secrets).
- `app/services/cost_tracker.py` — extracts token usage from `ChatGroq` responses, multiplies by a static per-model price table, logs to a local SQLite table (`resources/cost_log.db`, stdlib `sqlite3`).
- `scripts/check_cost_alert.py` — sums cost over a rolling window, sends a Slack webhook alert if over a configured threshold; runs as a scheduled GitHub Action or Container Apps cron job.
- `app/routers/admin.py` — `GET /admin/costs`, gated to `c-level` role only, returns aggregated cost stats.

## Verification approach throughout

- Phases 1-2: manual curl/pytest checks against role-based access rules (each role sees only what it should).
- Phase 3: manually exercise login → chat flow in the browser via the dev servers (`fastapi dev` + `vite dev`).
- Phase 4: `python scripts/run_eval.py` locally before trusting CI; confirm thresholds catch a deliberately broken RBAC filter (regression sanity check).
- Phase 5: hit the deployed Container Apps URL directly, repeat the role-based checks against the live environment.
- Phase 6: push a trivial change and confirm the eval gate blocks a failing PR, then confirm a passing one deploys automatically; verify a cost log row is written after a `/chat` call.

