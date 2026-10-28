# Initial audit report

Audit date: 2026-10-27. Branch: `SE`. Baseline commit: `a1ba944` (`feat: integrate SearXNG and Siftdog self-hosted retrieval with improved sourcing`). The worktree was already dirty with uncommitted routing/memory changes; those changes were inspected in place and preserved.

## Evidence inspected

Reviewed root configuration, README, Docker Compose, Python/npm dependencies, FastAPI bootstrap, config/database, models, message and RAG APIs, query router, conversation memory, RAG/LLM services, retrieval/reranking, ingestion, repo store, and the newly added router/memory tests. Source discovery found FastAPI, SQLAlchemy/PostgreSQL/pgvector, sentence-transformers, React/Vite/TypeScript, SearXNG/Siftdog/Tavily integration, provider fallbacks, and a substantial test/evaluation corpus.

## Verification run

* `py -3.14 -m compileall -q backend` — passed.
* `cd frontend; npm run build` — passed (TypeScript and Vite production build).
* Route smoke import/decision check — passed: comparison -> `COMPLEX_SAP`; greeting+definition -> `SIMPLE_SAP`; unrelated question -> `OUT_OF_DOMAIN`.
* `py -3.14 -m pytest -q backend/tests/test_rag_stream_authorization.py backend/tests/test_query_router.py -k "rag_stream_rejects_inaccessible or required_table_routes" --tb=short` — **17 passed, 12 deselected** in 2.28s.
* Full collection: `py -3.14 -m pytest --collect-only -qq backend/tests -m "not live"` — per-file output totaled 331 tests (3 marked live).
* Focused isolated-PostgreSQL command: `py -3.14 -m pytest -q backend/tests/test_conversation_memory.py backend/tests/test_memory_schema_migration.py backend/tests/test_rag_stream_authorization.py backend/tests/test_query_router.py backend/tests/test_followup_and_greetings.py -k "not existing_rag_citations and not conversational_rag_service_flow" --tb=short` — **54 passed, 2 deselected** in 27.25s. The first exclusion requires a populated SAP corpus; the second expects the legacy `conversational` source label while current direct routing emits `direct_llm`.
* `py -3.14 -m compileall -q backend` — passed after storage recovered.
* `py -3.14 -m pytest -q backend/tests/test_followup_and_greetings.py -k memory_followups_resolve_against_earlier_fica_context --tb=short` — **1 passed, 6 deselected**.
* `cd frontend; npm run build` — passed after changes (TypeScript and Vite production build).
* Database configuration: disposable `pgvector/pgvector:pg16` container exposed only on `127.0.0.1:55432`; focused run used database `sap_brim_ai_test` and full run used a separate fresh `sap_brim_full_test` database. `TEST_DATABASE_URL` was set to each `*_test` database per `backend/tests/conftest.py`. No production/shared database was used. LLM credentials were blank and web/repository fallback flags disabled.
* Full non-live run: `py -3.14 -m pytest -q backend/tests -m "not live" --tb=short` — incomplete, no final pytest counts. Python 3.14 terminated with a Windows access violation in Torch/Transformers during `sentence_transformers.encode`, called by document ingestion from `test_admin_ingestion_allowed_with_admin_key`.
* After the crash, Docker reported a read-only containerd metadata store; its disposable container could not be stopped/removed and exec was refused. C: temporarily reported 0 free bytes, later recovering to about 233 MB. An initial compile retry failed with `OSError: [Errno 28] No space left on device`; compilation and frontend build passed after recovery.
* Earlier initial-audit router invocations had no captured final result; they are superseded by the completed focused command above. The full focused memory file was also attempted without exclusions: 16 passed and its corpus-dependent citation test failed because the disposable database intentionally contained no SAP document chunks.

## Observed findings

* P1 fixed: component-comparison questions were explicitly classified as simple direct responses. That bypassed grounded retrieval for a relationship that can be release/process dependent. They now route as complex SAP; a parameterized regression case was added.
* P1 fixed: `/api/rag/query/stream` silently accepted a supplied nonexistent/foreign chat ID while `/api/rag/query` rejected it. It now returns 404 before generating/persisting.
* Fixed: rolling-summary coverage gap. The exact cause was that the updater received only the newest user/assistant strings, had no watermark, and never queried older message rows.
* New memory columns: added two nullable fields through the existing additive runtime migration convention; a legacy-shaped scratch-schema test verified idempotency and existing-row preservation. P2 open: overall `init_db()` remains non-versioned.
* P2 open: embedding generation occurs in request persistence paths and can add latency/fail independently; failures are logged and stored as null, but no measured latency/coverage evidence was collected.
* P3 open: earlier `git diff --check` reported a trailing blank line in `backend/app/models/message.py`; it could not be rerun after storage exhaustion.

## Security and architecture observations

The backend validates minimum secret requirements at startup and has user-scoped message-history queries. CORS currently allows all origins with credentials; assess deployment origin policy before production. Search/web and uploaded file contents must remain untrusted. Retrieval scores are relevance signals, not factual-accuracy percentages; calibration has not been independently evaluated here.

No production database, secrets, or external providers were accessed. No claim of production readiness is made.

## Follow-up: Docker/PostgreSQL startup and setup docs

Date: 2026-10-27. Existing uncommitted query/memory work was preserved.

### Diagnosis

* `docker compose ps -a` reports `sap_assistant_postgres` as `Up 5 hours (healthy)`, but `docker inspect` reports `Status=exited`, exit code 139, and error `open .../hosts: read-only file system`. Health history records successful `pg_isready` probes followed by `OCI runtime exec failed: "runc" executable not found`.
* `docker start sap_assistant_postgres` failed with the same internal read-only `hosts` path. `docker image inspect pgvector/pgvector:pg16` failed because the Docker Desktop containerd content blob returned `input/output error`.
* `docker exec ... pg_isready` reports the container is not running; `Test-NetConnection 127.0.0.1 -Port 5434` returned false. Thus the reported Compose status is stale/inconsistent and the database is unavailable.
* `wsl --status` reports WSL default version 2; `wsl --list --verbose` shows the `docker-desktop` distribution running and Ubuntu stopped. At inspection time C: had about 6.3 GB free, so current host C: exhaustion was not observed. This does not establish the underlying Docker Desktop VHD/containerd cause.
* The stopped container's host binding is configured as `127.0.0.1:5434` -> `5432`, and its data mount is `sap_brim_pgdata`. `docker volume inspect` confirms that named volume exists. No database listing/count query or backup succeeded; contents, database presence, and integrity remain unverified.
* The repository expects database/role `sap_brim_ai`; Compose defaults `POSTGRES_DB`/`POSTGRES_USER` to `sap_assistant`, and the first-initialization script creates the separate application database/role. The script does not run on an existing data directory. The actual databases in the volume could not be queried.
* Loaded backend settings were inspected without printing credentials: the active URL resolves to host `127.0.0.1`, port `5434`, database/role `sap_brim_ai`; root Compose port is also `5434`, and the URL password matches `SAP_BRIM_DB_PASSWORD`. PostgreSQL authentication itself could not be exercised.
* Docker configuration has been aligned to the observed intended port 5434. `docker compose config --quiet` passes and rendered port is 5434. Rendered volume names are `sap_brim_pgdata` for the normal project and `sap_brim_fresh_pgdata` for the documented alternate fresh project.
* Root cause established: Docker Desktop/containerd internal storage/runtime failure. The lower-level cause in WSL2 or host disk is not established. No containers/images/volumes were removed or recreated; no backup was created.

### Changes and checks

* Updated `docker-compose.yml`, `.env.example`, and `backend/.env.example` to default PostgreSQL to host port 5434 and corrected the stale shared-volume comment.
* Rewrote the existing README setup section with Windows PowerShell setup/start-after-restart, actual service names and URLs, health checks, database safety, backup/restore, fresh-volume steps, and explicit blocker/known limitations. Aligned `docker.md` to port 5434 and the verified volume name.
* `docker compose config --quiet` — passed. Rendered config check — PostgreSQL host port 5434; normal and alternate project volumes distinct as above.
* `py -3.14 -m compileall -q backend` — passed.
* `Push-Location frontend; npm run build; Pop-Location` — passed; TypeScript and Vite 8.3.3 built 2,601 modules.
* `git diff --check` on the README, Docker config, and environment examples — passed. Full-worktree `git diff --check` still reports the pre-existing extra blank line at `backend/app/models/message.py:29`; that user change was left untouched. New engineering-memory Markdown files were checked for trailing whitespace and passed.
* Database startup/readiness/SQL counts, backend `/health`, integration tests, and backup/restore remain blocked by Docker errors. No database-backed test is claimed as passed for this follow-up.

### Documentation changes

Updated this report, `PROJECT_CONTEXT.md`, `IMPLEMENTATION_MAP.md`, `IMPLEMENTATION_STATUS.md`, `KNOWN_ISSUES.md`, `CHANGELOG_ENGINEERING.md`, and `NEXT_SESSION.md`. `AGENTS.md` remains accurate and was not changed.

## Recovery after user follow-up

Date: 2026-10-27.

* `docker start sap_assistant_postgres` still failed on the read-only container `hosts` path. `docker desktop restart` then left Desktop in `starting` and status reported unable to start.
* Filtered Docker Desktop error logs identified the WSL cause: `wsl-bootstrap` failed formatting `/dev/sde` (`mkfs` exit status 1), and Docker Desktop could not detach `docker_data.vhdx` (`Operation not permitted`); the log recommended `wsl.exe --shutdown`.
* Ran `wsl --shutdown` (Ubuntu was already stopped; this stopped the Docker Desktop WSL distro), then `docker desktop start`. Desktop returned to `running`; existing PostgreSQL, SearXNG, and Siftdog containers resumed with their original volumes. No containers or volumes were removed.
* `docker compose up -d postgres searxng siftdog` succeeded and reported the existing containers running. PostgreSQL health was `healthy`, host mapping `127.0.0.1:5434->5432`, and `Test-NetConnection` passed.
* Read-only SQL confirmed databases `postgres`, `sap_assistant`, `sap_brim_ai`, `sap_brim_ai_test`; app DB `sap_brim_ai`; vector extension 0.8.7; counts: 62 documents, 12,406 chunks, 2 users, 1 chat, 6 messages. The configured bootstrap role `sap_assistant` is absent (role list includes `postgres` and `sap_brim_ai`); `pg_isready` reports server readiness without validating user authentication. The app role connected successfully.
* Started backend with `py -3.14 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload`. Startup initialized/verified schema and succeeded. `/health` returned healthy with 62 documents and 12,406 chunks. `/docs`, frontend `/`, Siftdog `/health`, and SearXNG `/` each returned HTTP 200. The Vite dev server remains running on port 5173.
* No logical or raw volume backup was created. The recovered database was queried but not exhaustively integrity-checked.
