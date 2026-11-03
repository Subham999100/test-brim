# Known issues

## UI-001 — Tailwind colour utilities have no effect on `<button>` elements

* Severity: P3 (visual; app-wide)
* Observed 2026-11-03 in headless-Edge screenshots of `ChatMessage`: `frontend/src/index.css` line 17 has `button{color:inherit}` outside any CSS layer. In Tailwind v4, un-layered CSS beats every utility class, so `text-*` and `hover:text-*` on a `<button>` are ignored and the button takes its parent's colour. Example: the answer action icons (`promptActionClass`, meant to be `text-slate-400`) render in the body ink colour.
* Workaround used: the disclaimer's Regenerate link puts its colour on an inner `<span>`.
* Fix: move the rule into `@layer base { button { color: inherit; } }`. This changes the colour of every button whose `text-*` class was being ignored, so review the main pages visually before shipping it.
* Status: open (owner decision).

## LLM-002 — Local provider configuration names unusable models

* Severity: P2 (owner action; `.env` not edited)
* Observed 2026-11-02 with a one-word live probe per configured model:
  - `LLM_MODEL=llama-3.3-70b-versatile` returns 404 `model_not_found` for this Groq key, so the first Groq call after every 1-hour cooldown is wasted;
  - `gemini-3.8-flash` returns 429 quota exceeded;
  - `apodex/apodex-1.1-mini:free` is no longer served by OpenRouter (now removed from the code defaults).
  - Every other configured model answered: Groq qwen/qwen3.8-27b, gpt-oss-120b, gpt-oss-20b and allam-2-7b; gemini-2.5-flash; OpenRouter liquid and nemotron.
* Fix: set `LLM_MODEL` to a model the key can use (for example `openai/gpt-oss-120b`, as in `.env.example`), and drop `apodex/...` from `LLM_OPENROUTER_MODELS` if the local `.env` sets it.
* Status: open (owner).

## TEST-002 — Rate-limit expiry test depends on host uptime

* Severity: P3 (test bug, not a product bug)
* Affected: `backend/tests/test_audit_auth.py::test_f06_memory_backend_caps_keys_and_expires_buckets`
* Observed 2026-11-02: it fails whenever the host has been up for more than about 2.8 hours. The test patches `time.monotonic` to return `10_000.0` to simulate "later", but on Windows `monotonic()` is system uptime (11,435 s at the time), so 10,000 lies in the past.
* Proposed fix: patch to `time.monotonic() + 10_000`. Not changed (unrelated to the fallback work).
* Status: open.

## LLM-003 — No whole-request deadline across the LLM tiers

* Severity: P3
* Observed: each model call times out after 45 s and timeouts put the model on a 60 s cooldown, but a request whose every model times out can wait up to 9 x 45 s before the web-search fallback runs.
* Proposed fix: a per-request generation deadline that skips the remaining tiers and goes straight to web search.
* Status: open.

## DOC-001 — Compose stack is for local dependencies

* Severity: Informational
* Observed: Docker Compose runs PostgreSQL/pgvector; optional SAP web search is through Tavily. FastAPI and React/Vite are run on the host for development.
* Guidance: use `SETUP.md` for a fresh checkout (`docker-setup/README.md` now points there). It is not a production deployment manifest.
* Status: documented.

## SEC-001 — Security audit remediation incomplete

* Severity: P1
* Observed: initial fixes cover public demo login, privilege assignment, token expiry/revocation, direct RAG metadata, bounded uploads with signature and PDF page checks, process-local rate limits, admin SSE token URLs, explicit CORS, response headers, and share revocation.
* Remaining: MFA and renewal tokens, distributed/per-user rate limiting and hash concurrency bounds, streamed evidence-marker stripping, parser extraction timeouts and decompression limits, shared-link expiry, encrypted/tested backups, complete dependency scan/upgrades, and full isolated-database suite. Production TLS/proxy/header configuration must be verified at deployment.
* Verification details: `NEXT_SESSION.md`.
* Status: partial; follow-up required.

## DB-001 ? Migration behavior needs deployment verification

* Severity: P2
* Affected files: `backend/alembic.ini`, `backend/migrations/versions/`
* Observed: Alembic revisions 0001 through 0004 manage application schema changes; startup applies pending migrations only when `AUTO_MIGRATE=true`.
* Remaining: verify rollout and restore procedures against a production-like backup before enabling automatic migration in production.
* Status: migration framework implemented; deployment verification open.

## MEM-001 — Rolling summary is bounded and lossy

* Severity: P2
* Affected files: `backend/app/services/conversation_memory_service.py`, `backend/app/models/chat.py`, `backend/app/database.py`
* Observed: ordered old-message excerpts are processed once, but each excerpt caps at 500 characters and the aggregate summary caps at 4,000 characters, retaining only its tail.
* Root cause: deliberate bounded extractive summary; it is not a transcript.
* Proposed fix: evaluate usefulness before changing limits; full messages remain available through history retrieval.
* Status: partial by design.
* Regression tests: `test_16_summary_covers_messages_that_leave_recent_window_and_is_idempotent`, `test_19_concurrent_summary_updates_do_not_duplicate_excerpts`, and `test_17_summary_failure_does_not_advance_watermark`.

## QA-001 — Focused pytest result not captured

* Severity: P2
* Affected files: test execution environment.
* Observed: the runner returned partial dots and detached before pytest emitted its final summary.
* Expected: a completed report with exit status, passed/failed/skipped counts.
* Root cause: unconfirmed; likely execution-wrapper timeout/streaming behavior.
* Status: resolved for this session: focused isolated suite completed with 54 passed and 2 deselected.

## QA-002 — Full suite blocked by local runtime/storage failure

* Severity: P2
* Affected files: test environment; `backend/tests/test_security.py` triggers ingestion.
* Reproduction: `py -3.14 -m pytest -q backend/tests -m "not live" --tb=short` against isolated PostgreSQL.
* Observed: Python 3.14 access violation in Torch/Transformers during batch embedding inside ingestion. Docker then reported a read-only containerd metadata store and C: had no free bytes.
* Expected: completed suite summary and recoverable test container.
* Root cause: Python extension crash observed; Docker metadata cause is unknown.
* Proposed fix: restore Docker Desktop storage, then rerun ingestion on a supported stable Python/Torch runtime.
* Status: environment blocked; pytest counts unavailable.

## DOCKER-001 — Docker Desktop WSL data-disk startup failure

* Severity: P1 for local startup; recovered on 2026-10-27.
* Affected configuration: Docker Desktop/containerd and existing `sap_assistant_postgres` container.
* Initial evidence: read-only internal container `hosts` path, missing `runc`, containerd image blob I/O error, host port 5434 refused. A normal container start and Docker Desktop restart did not recover it.
* Root cause evidence from Docker Desktop logs: `wsl-bootstrap` failed formatting `/dev/sde` (`mkfs` exit 1), then WSL could not detach `docker_data.vhdx` (`Operation not permitted`). The deeper reason for the VHD formatting/detach failure remains unknown.
* Recovery: ran `wsl --shutdown` after saving work; then `docker desktop start`. Existing containers and volume resumed. No factory reset, volume deletion, or container removal occurred.
* Historical verification (2026-10-27): PostgreSQL was healthy on 5434; app database role connected; backend `/health` was healthy with 62 documents and 12,406 chunks. On 2026-10-31, port 5434 had no listener and this session could not access Docker Engine. No backup artifact has been created.
* Separate health-check limitation: Compose's `pg_isready -U sap_assistant -d sap_assistant` reports server readiness but does not authenticate. The existing cluster has database `sap_assistant` but no role `sap_assistant`; app role `sap_brim_ai` works. Backend `/health` is the verified app-level connection check.
* Status: recovered; monitor Docker Desktop startup. Back up the logical cluster before any future reset/recreation.
## PERF-001 - Scholar (RAG) answers are slow by design of the serial pipeline

* Severity: High (user-facing latency)
* Observed in code (not profiled against live providers): every stage runs serially in one request thread. Main costs, largest first:
  * LLM provider cascade: `generate_answer` and `generate_completion` try every configured model of Groq, then Gemini, then OpenRouter, each with a 45 s timeout and no whole-request deadline or circuit breaker. A Groq `finish_reason=length` discards the output and regenerates on the next model.
  * Up to 4-6 LLM calls per answer: optional answer-style classifier (Groq, 4 s timeout, rule miss only), generation, repair after a failed grounding gate, and a full web-backed regeneration plus repair when the gate still fails.
  * Web fallback fires when `document_match_score < DOCUMENT_MATCH_THRESHOLD` (0.80). Calibrated rerank scores for real chunks are typically ~0.5-0.75 (see the 0.5425 CI-query observation), so Tavily likely runs on most Scholar queries; it can make two sequential calls (help.sap.com, then all approved domains) with raw page content.
  * Retrieval is repeated per aspect: up to 11 scenario aspects plus up to 5 restriction-scope expansions, each with COUNT(*), query embedding, a full 12,406 x 384 matrix product and a Python BM25 loop.
  * Grounding verification runs up to three times per candidate (initial, after repair, after guard) and again on the web retry.
  * Streaming buffers the whole verified answer before the first token (F-03), so time-to-first-token equals total pipeline time.
  * Cold start: the embedding model and the full chunk table with vectors load on the first query, and again whenever the chunk count changes.
* Guidance: measure stage timings first (diagnostics already record `elapsed_time_ms`); likely wins are a whole-request deadline, fewer models per provider with shorter timeouts, a calibrated `DOCUMENT_MATCH_THRESHOLD`, parallel aspect retrieval or batched aspect embeddings, and warming the embedding model/cache at startup.
* Status: open. Redundant scoring loops in grounding/retrieval were removed on 2026-10-31 (output-identical); the structural causes above remain.
* Measured 2026-11-01 (live providers, `sap_brim_ai_test` with 31,247 chunks, owner `.env`): index build 9.6-10.0 s inside the first request (about 4 s row load, 6 s Python indexing); Tavily 2.5-4.8 s per search; Groq generation 2-3 s; `LLM_MODEL=llama-3.3-70b-versatile` returns 404 on every call. With `MULTI_SOURCE_COMPARE_ENABLED=true` (owner `.env`; default false) the comparator web-searches every Scholar question, even at document match 0.92-0.98, and web evidence won both comparisons. A 6-part incident question took 69 s: Groq free-tier per-minute token limits rejected the 5.4k-token prompt (429/413), so Gemini wrote it in 34 s, then the grounding repair regenerated it on Gemini in 25 s.
* Fixed 2026-11-01: index warm-up off the request path at startup and 5 s after invalidation (`RETRIEVAL_CACHE_WARMUP`); comparator searches question parts concurrently (6 parts: 27.4 s sequential sum, 8.6 s wall); `ModelCooldowns` skips models after 404/decommissioned (1 h), 429 (retry-after, else 30 s) or timeout (60 s); query rewriter has no hidden SDK retries and a 10 s timeout. Measured after: first question after startup 16.8 s to 9.6 s, a typical question 6.2 s to 5.2 s.
* Still open (owner decisions): comparator web search on every question while compare mode is on; the 404 `LLM_MODEL`; Groq TPM tier for large prompts; the repair pass regenerating the full answer; answers buffered until verification (F-03); about 5 s of Hugging Face Hub checks at startup (`HF_HUB_OFFLINE=1` once the model is cached).

# RAG generation availability

The RAG pipeline no longer converts retrieved passages into fallback answer text. If no allowed model produces a candidate, clients receive a generic unavailable answer and `verification_status: "unavailable"`; rejected grounding triggers one web-backed retry when enabled, then fails closed if still unsupported. Default provider order is Groq, Gemini, OpenRouter; explicitly empty allowlists disable external calls. Runtime provider credentials and quotas remain unverified because secrets and `.env` contents were intentionally not inspected. There is no provider circuit breaker or whole-request deadline.

## ENV-002 - Low-memory host destabilises long test runs

* Severity: Medium (verification reliability)
* Observed 2026-11-01: with about 1.5 GB free RAM, the Docker VM restarted during `test_audit_access.py`, OpenBLAS could not allocate in the `test_f42` subprocess, combined pytest runs crashed with Windows access violations, and Vitest fork workers timed out. All affected tests passed when rerun in isolation.
* Workaround: one pytest file per process with `OPENBLAS_NUM_THREADS=1`; `npx vitest run --maxWorkers=1`; stop scratch servers before test runs.
* Status: open (host capacity).

## DB-002 - Dev server auto-migrates the real database on reload

* Severity: Medium
* Observed 2026-11-01: `uvicorn --reload` with the default `AUTO_MIGRATE=true` applied `0006_organisations` to the real `sap_brim_ai` database as soon as new backend files appeared. Additive, verified harmless this time.
* Guidance: set `AUTO_MIGRATE=false` for the dev server during schema work and migrate deliberately after a backup.
* Status: open.

## SETUP-001 - Fresh installs retrieve nothing until document tiers are set

* Severity: P2
* Affected files: `backend/app/models/document.py`, `backend/app/ingestion/ingest.py`, `backend/app/services/document_processing_service.py`, `backend/migrations/versions/0004_document_source_tier.py`
* Observed: new `Document` rows default to `source_tier="self_authored"` and `retrieval_service.hybrid_search` skips that tier unless `INCLUDE_SELF_AUTHORED_DOCS=True`. Migration 0004 back-fills the reviewed `DOCUMENT_TIER_MAPPING` only for rows that already exist, and neither ingestion path applies the mapping, so on a fresh database every ingested document is excluded from Scholar retrieval. The admin UI has no tier control (`PATCH /api/documents/{id}/tier` only).
* Workaround: documented in `SETUP.md` §9.3 (`INCLUDE_SELF_AUTHORED_DOCS=True` for development, or set tiers via the API).
* Fix needs an owner decision: apply `DOCUMENT_TIER_MAPPING` at ingestion time and/or add a tier control to the Document Manager.
* Status: open.

## FE-001 - Frontend API address is hard-coded

* Severity: P2 (blocks any non-localhost deployment)
* Affected files: `frontend/src/services/api.ts` (`API_BASE_URL`), unused `frontend/src/components/chat/RAGInspectorPanel.tsx`
* Observed: the SPA always calls `http://localhost:8000/api`; `VITE_API_BASE_URL` only feeds the build-time CSP in `vite.config.ts`. The Vite `/api` proxy is unused. Same as AUDIT_REPORT F-11.
* Status: open; documented in `SETUP.md` §15 and README "Known limitations".

## API-001 - Smaller inconsistencies found during the 2026-11-02 documentation review

* `.markdown` is accepted by admin upload (`SUPPORTED_EXTENSIONS`) but `document_extractor.extract_document` has no branch for it, so processing such a file would fail.
* `POST /api/rag/query` still returns `source_type`, `grounding_score`, `verification_status` and `external_search_used` to non-admins, unlike the chat message endpoints.
* `POST /api/chats/extract-document` docstring says 25 MB; the code limit is 10 MB.
* Swagger "Authorize" uses `tokenUrl=/api/auth/login`, which expects JSON, so the OAuth2 password form probably does not work (unverified); paste a token instead.
* Several settings have no runtime effect (`GROUNDED_*`, `CONTEXT_*`, `DEDUPE_SIMILARITY_THRESHOLD`, `ENABLE_SENTENCE_COMPRESSION`, `SHADOW_MODE_ENABLED`, `USE_CORPUS_METADATA_V2`, `RATE_LIMIT_MAX_RETRIES`, `RATE_LIMIT_BASE_BACKOFF_SEC`, `TIER_WEIGHT_OFFICIAL_DEV_DOCS`, `TIER_WEIGHT_OFFICIAL_HELP_DOCS`, `TIER_WEIGHT_SAP_COMMUNITY`).
* Status: open; not changed in the documentation pass.
