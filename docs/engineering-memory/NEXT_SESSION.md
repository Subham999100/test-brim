# Next session handover

## Document Manager bulk delete (2026-11-03)

Super admin > Knowledge base > Document Manager & Ingestion now has row checkboxes, a select-all box, and "Delete selected (N)" with a confirmation modal. Deletion loops over the existing single-document endpoint (`services/bulkDeleteDocuments.ts`); the backend was not changed. Verification: full Vitest suite passed (15 files, 81 tests, including 3 new `bulkDeleteDocuments` tests); `tsc -b --noEmit` produced no errors; eslint reported no errors on the changed files; `npm run build` succeeded; `git diff --check` passed. Unverified: the checkbox/modal flow in a real browser and real deletion against the database (no DOM test environment; the app was not launched). Select-all covers only the at most 100 documents loaded by the page. Uncommitted.

## Super admin dashboard toggles (2026-11-03)

Accounts and Knowledge base in the super admin header are now toggles that reveal their own sub-options (`AdminDashboard.tsx`). Verification: full Vitest suite passed (14 files, 78 tests); `tsc -b --noEmit` produced no errors; eslint reported no errors on the changed files; `git diff --check` passed. Unverified: toggle click behaviour in a real browser (no DOM test environment; the app was not launched). Uncommitted.

## RAG failure remediation (2026-10-29)

Removed the evidence-excerpt fallback from LLM generation. When no allowed provider produces text, the API returns a stable unavailable message with null grounding and `verification_status: "unavailable"`; the RAG path skips verification for this state and fails closed on rejected grounding. Provider failures are classified without storing exception text in diagnostics. Regular-user JSON and SSE expose only the unavailable status, while model/provider and failure details remain internal. See `RAG_FAILURE_DIAGNOSIS.md`.

Committed locally as `8b59675` on `audit-fixes`; no push was performed.

## Provider and web fallback follow-up (2026-10-29)

Committed locally as `8641fc3` on `audit-fixes`; no push was performed.

Fixed provider activation defaults: Groq, Gemini, and OpenRouter are now allowed in tier order by default; configured OpenRouter free models are enabled unless `LLM_ALLOW_FREE_TIER=false`; `LLM_PROVIDER=local` uses that allowlisted tier order, while an explicitly empty `LLM_ALLOWED_PROVIDERS` still disables external calls. Corrected RAG web fallback so a low document match triggers web search even when confidence is high and GitHub/multi-source comparison is disabled. Unified search now continues from empty Siftdog/SearXNG results to Tavily. `.env.example` documents the allowlist; the actual `.env` files were not read or changed.

Also added a single web-backed regeneration attempt if the grounding gate rejects an answer even though retrieval scores are strong. Offline focused verification passed 46 backend tests with fake provider/search results, `_env_file=None` applied before app settings construction, and a fake `_test` database URL. Runtime keys, provider quotas, Tavily availability, and network access remain unverified.

Focused verification passed: `test_rag_generation_unavailable.py` plus `test_audit_rag_pipeline.py` (16 passed). It used stubbed providers, offline retrieval, and a fake `_test` database URL; `.env` discovery was disabled before app imports. No real DB or provider was contacted. Runtime `.env` configuration, keys, quotas, and failure rates remain unverified. The current pasted task attachment was truncated mid-sentence, so any instructions after that point were unavailable. Do not stage existing owner edits in `README.md`, `backend/.env.example`, or engineering-memory files.

## Audit remediation continuation (2026-10-29)

Phase 3 continued on branch `audit-fixes`. F-20 is committed as `0da1283`: uploads spool in chunks with per-file and aggregate caps, signature checks, an opt-in extended-format set, a PDF page cap, and chunk-counted request body limits. PDF extraction timeout remains open. F-21 query length is capped at 4,000 characters; daily budgets and message/attachment caps remain open. F-52 hostname checks now use exact/subdomain matching across registry, comparison, confidence, and context-tier paths; commits `80dda9a` and `c67b5e4`. Its focused regression passed. F-53 is committed as `bedece9`: Alembic 0004 adds `documents.source_tier`, defaults unclassified records to `self_authored`, backfills reviewed historical filename tiers, exposes an audited admin classification endpoint, and feeds the tier into retrieval/confidence/context weighting. F-08/F-54 partial safeguards are committed as `704e8fa`: `INCLUDE_SELF_AUTHORED_DOCS=false` excludes project-authored evidence before ranking, misleading generator labels are removed, and owner review is documented in `HUMAN_ACTIONS.md`; existing PDFs and orphaned DB rows remain untouched. F-31 safeguards are committed as `12244f8`: authenticated export and cascade deletion, final-admin protection, plus a 365-day attachment cleanup command that defaults to dry-run.

F-32 is committed as `2fd98a7`: browser profiles, projects, pinned chats, and archived chats are scoped by user ID; logout clears the current user's scoped values and legacy global keys are removed without migration. F-46 is committed as `6e3f0c5` and `88c0879`: upload/delete/processing failures use generic codes in API/SSE and persisted status, with exception details retained in server logs. Verification passed: frontend storage tests (3), full Vitest suite (17), TypeScript check, lint (warnings only), and backend generic error tests (3). No push was performed.

F-07 is partially implemented and committed as `381485e`: hash fallback removed; `EMBEDDING_MODEL` config is honored by both backends; chunks/messages record model/version; dense retrieval excludes incompatible vectors while lexical/identifier retrieval remains; ingestion rebuilds documents whose stored vector provenance differs. Revision 0005 labels pre-existing vectors `legacy-unknown`. Focused embedding/access/migration/retrieval/memory tests passed (42 passed, 5 live deselected). Re-embedding the real corpus was not run; see `HUMAN_ACTIONS.md`. No push was performed.

Earlier commits on this branch: `12244f8` (F-31 partial), `704e8fa` (F-08/F-54 partial), `bedece9` (F-53), `c67b5e4`, `80dda9a` (F-52 partial), `0da1283` (F-20 partial), `1ddf54e` (F-09/F-10/F-21), `0432603` (F-45), `f0a89d6` and `c5625fd` (F-50), `e48a579` (F-05), and `e84d22e` (F-24). No remote was contacted. Owner changes to `README.md`, `backend/.env.example`, and `docs/engineering-memory/*` remain unstaged.

Verification this continuation: F-20 focused security/provider/RAG/upload selection passed 72 tests. F-52/F-53 focused regression, upload-default, and migration selection passed 5 tests; changed F-53 modules compiled with `py_compile`; `git diff --check` passed. Tests that import the retrieval stack need `HF_HUB_OFFLINE=true` on this host to prevent blocked model downloads. Backend `ruff` is unavailable. F-08/F-54 focused tests passed (3 passed); the upload/process/classify/retrieve integration passed (1 passed). F-31 account export/deletion/retention and final-admin protection tests passed (4 passed); database backups remain an owner/deployment action. The earlier full backend baseline stalled at 34% and was interrupted without a final result.

Remaining: most Phase 3 findings and Phases 4 through 6 remain open. F-20 extraction timeout, F-21 daily per-user budgets and message/attachment caps, F-52 upstream web license/gate metadata trust, F-08 identifier-claim evidence enforcement and F-54 orphan-record cleanup; F-31 verified encrypted backups, direct PostgreSQL retrieval, ingestion reliability, dependency/Docker/CI changes, and the human-authored evaluation runner/metrics remain. No corpus re-chunk/re-embed was run. Keep all user work outside the explicit audit commit paths unstaged.

## Audit remediation in progress (branch `audit-fixes`, local only, not pushed)

Phases 1–2 of the fixes for `AUDIT_REPORT.md` (untracked, root) are committed: 15 findings fixed, F-26/F-27/F-33 partial. Read `AUDIT_FIX_LOG.md` (status per finding, before/after test numbers), `HUMAN_ACTIONS.md` (secret rotation, history rewrite, licensing, provider approval, the backup to take **before** first starting this branch against the real DB, SSO/BFF plan) and `CHANGELOG_AUDIT.md` (API/config changes, incl. breaking: registration off by default, new JWT claims, save-partial body). Schema is now Alembic-managed (`backend/alembic.ini`, revisions 0001–0003); startup migrates when `AUTO_MIGRATE=true`. Next: Phase 3 (prompt injection/output filtering F-09/F-10, LLM egress F-05, logging F-24, limits F-20/F-21, F-52/F-53, F-08/F-54, F-31, F-32, F-46). Test command: blank the LLM/search keys, set `DEBUG=false WEB_FALLBACK_ENABLED=false`, run `pytest backend/tests -m "not live"` against `sap_brim_ai_test` (container `sap_assistant_postgres`). After Phase 2: 411 passed, 6 pre-existing failures (listed in the log). A scratch DB `sap_brim_ai_empty_test` exists for the fresh-build migration test.

## Setup documentation update (2026-10-28)

Added `docker-setup/README.md` as a portable new-machine guide. The root README links to it, drops workstation-specific paths, and corrects outdated guest and admin-provisioning instructions. `backend/.env.example` now matches the 15-minute access-token setting and documents development CORS origins. No actual `.env` values were used in documentation. Verification: `docker compose config --quiet` exited successfully (Docker CLI emitted a local config-file access warning); documented relative paths exist; `git diff --check` passed. No application tests were run for this documentation-only change.

## Security remediation handover (2026-10-28)

This session implemented an initial security remediation based on the untracked `backend/tests/test_security_audit_characterization.py`; the referenced `SECURITY_AUDIT_REPORT.md` was not present in the checkout. Existing user work was preserved and the characterization test was replaced with secure behavior regressions.

Changed: public demo login and browser guest/trial fallback removed; registration always creates consultant/non-admin accounts and password minimum raised to 12 characters with a bcrypt 72-byte cap; existing configured admin email is no longer auto-promoted; access JWTs shortened to 15 minutes, require standard claims and token version, and `/auth/logout` revokes all existing tokens for that user; document extraction requires authentication, reads at most 10 MiB plus one byte, and validates a file extension allowlist; synchronous and streaming direct RAG responses strip citations/evidence scores/comparison metadata for regular users; server-side process-local request limits and content-length rejection added; CORS now uses configured origins, production refuses wildcard origins and rejects HTTP; basic browser security headers added; administrator processing SSE uses Authorization header through fetch streaming instead of URL query credentials; share links have owner-controlled revocation and an explicit disclosure; hardcoded SearXNG fallback secret removed.

Verification: 20 focused backend security/auth/RAG/extraction tests passed after updating legacy tests to use authenticated test principals. Frontend `npm.cmd test` passed (10 tests), `npm.cmd run build` passed, `py -3.14 -m compileall -q backend` passed, and `git diff --check` passed. The first backend test invocation was blocked by invalid local `DEBUG=release`; setting process `DEBUG=false` allowed tests to run. `npm.cmd audit --omit=dev` could not reach the npm advisory endpoint; `pip_audit` is not installed. No dependency upgrade/lockfile resolution was completed.

Remaining security work/blockers: no MFA; no refresh-token renewal flow (short access tokens currently require re-login); rate buckets are per process and not shared across replicas, with no password-hash concurrency semaphore; content-length rejection does not protect chunked requests and multipart parsing happens before endpoint byte checks; document parser resource limits/content-signature validation need dedicated hardening; shared links have revocation but no expiry setting; validate logout/revocation against real PostgreSQL and run wider suite. Admin provisioning remains operator-managed by provisioning the account outside public registration; current startup only creates a new account when configured email is absent and does not grant privileges to an existing matching account. Production TLS termination, trusted proxy scheme forwarding, origin values, HSTS, and deployment-level CSP/security headers remain unverified assumptions. Pin/scan dependency tree using reachable scanner and review the supplied audit report if added to workspace.

Current branch: `security-remediation-20261028`. The security remediation commit is local and was not pushed because its branch history includes knowledge-base PDFs and internal reports excluded from the user's push authorization.

## Current application state

Docker Desktop was recovered after WSL logs showed `/dev/sde` formatting failed (`mkfs` exit 1) and `docker_data.vhdx` could not detach. `wsl --shutdown` followed by `docker desktop start` brought Docker Desktop back without deleting containers or volumes. The existing `sap_brim_pgdata` volume remains attached.

`docker compose up -d postgres searxng siftdog` succeeds. PostgreSQL is healthy on `127.0.0.1:5434`; `sap_brim_ai` app role/database works. Backend was launched with `py -3.14 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload`; `/health` reports healthy, 62 documents, 12,406 chunks. Frontend Vite is running at 127.0.0.1:5173. Swagger `/docs`, frontend `/`, Siftdog `/health`, and SearXNG `/` returned HTTP 200.

Database snapshot via read-only SQL: databases `postgres`, `sap_assistant`, `sap_brim_ai`, and `sap_brim_ai_test`; 62 documents, 12,406 chunks, 2 users, 1 chat, 6 messages; pgvector 0.8.7. No backup was created. Do not claim a backup exists or reset Docker/volumes before making and verifying one.

Compose health-check caveat: `pg_isready -U sap_assistant -d sap_assistant` is only a server readiness probe and does not authenticate. The `sap_assistant` database exists but the `sap_assistant` role is absent in the existing cluster; `sap_brim_ai` role connects and backend `/health` proves the app connection. Consider aligning healthcheck with an authenticated SQL query, but assess whether it will recreate the PG container and back up first.

## Checks and blockers

* `docker compose up -d postgres searxng siftdog` — passed after WSL recovery; all three containers running.
* `docker exec sap_assistant_postgres pg_isready -U sap_assistant -d sap_assistant` — readiness returned true, but see authentication caveat above.
* `Test-NetConnection 127.0.0.1 -Port 5434` — passed.
* Read-only SQL counts and vector extension — passed; see `AUDIT_REPORT.md`.
* Backend `/health`, `/docs`, frontend `/`, Siftdog `/health`, SearXNG `/` — HTTP 200/healthy.
* Backend compilation and frontend build passed in the previous task. The full backend suite previously collected 331 tests but crashed in Python 3.14 Torch/Transformers during admin ingestion before final counts; not rerun after Docker recovery.
* Full regression run on updated RAG pipeline (`backend/tests/test_adaptive_rag_pipeline.py`, `backend/tests/test_solution_design_answers.py`, `backend/tests/test_senior_upgrade_and_reconciliation.py`, `backend/tests/test_answer_style_router.py`, `backend/tests/test_sap_restriction.py`, `backend/tests/test_citation_provenance.py`, `backend/tests/test_security.py`) passed (80 passed in 7.03s).
* No DB backup/restore created yet.

## Current RAG Answer Generation State

Adaptive response generation for complex SAP BRIM scenarios has been implemented:
1. `answer_planner.py`: Added `production_incident` archetype with mandatory 10-section structure.
2. `answer_style_router.py`: `production_incident` routed with max_sections=10, detailed level, procedural steps, and 10-section layout.
3. `evidence_selection_service.py`: Dynamic scaling of internal_top_k up to 16 chunks for multi-aspect incident queries (replaces rigid 4-chunk bottleneck).
4. `rag_service.py`: Incident aspect splitting across CC, CI, FI-CA, safe recovery, and reconciliation. Diagnostic tracking in `process_query` and `stream_query`.
5. `llm_service.py`: Output continuation on length cutoff (`_continue_gemini`, `_continue_openrouter`), token diagnostic tracking, adaptive word targets (100–250 words simple, 400–800 words intermediate, 1,200–2,000 words complex incident target).
6. Tests: `backend/tests/test_adaptive_rag_pipeline.py` (10 tests covering Tests A–F) all passing.

Next three tasks:

1. Create and verify an external logical backup of `sap_brim_ai` and, if required, the full cluster before any reset/recreation.
2. Run end-to-end frontend integration tests with streaming and verifying that long Markdown answers (including all 10 incident sections) render seamlessly in the UI without markdown breakage.
3. Decide whether to repair the Compose healthcheck's nonexistent `sap_assistant` role assumption; back up first if applying the change would recreate PostgreSQL. Keep all existing volumes and unrelated containers.

Read first: `PROJECT_CONTEXT.md`, `IMPLEMENTATION_MAP.md`, `AUDIT_REPORT.md`, then `KNOWN_ISSUES.md` and the affected README/Docker configuration.


## Python version guidance (2026-10-31)

Updated user-facing setup guidance and actionable backend migration/compile examples to standardize on Python 3.12. Historical audit commands and outcomes remain unchanged because they record the Python 3.14 environment used at the time. git diff --check passed; no tests were run for this documentation and command-text update. Runtime verification under Python 3.12 remains unverified. Preserve existing owner edits to engineering-memory files and other modified files.

## Python 3.12 project pin (2026-10-31)

Added repository .python-version set to 3.12; backend requirements identify the supported runtime; README and Docker setup create venvs explicitly with py -3.12 on Windows or python3.12 on macOS/Linux; actionable maintenance/deployment commands now use 3.12. py -3.12 --version was attempted and reported no suitable Python runtime installed/registered. Therefore the project files are pinned, but this workstation runtime/dependency installation has not been migrated or verified. No tests were run. git diff --check passed. Historical audit records remain in their original Python version context.

## Python 3.12 runtime installation follow-up (2026-10-31)

Installed Python 3.12.10 with winget from the verified python.org installer. The legacy Windows py launcher still lists only system Python 3.14, so py -3.12 is unavailable on this machine; the per-user interpreter is at %LOCALAPPDATA%\Programs\Python\Python312\python.exe. Created project .venv with that interpreter and installed ackend/requirements.txt. Verification passed: .venv\Scripts\python.exe --version reports Python 3.12.10; pip check reported no broken requirements; backend compileall passed; git diff --check passed. No tests were run. Keep using the activated .venv for local backend commands. The prior 3.12-pinned setup instructions assume Python launcher registration and should be adjusted if a fresh Windows install also fails to register with py.

## Sprint and Scholar chat modes (2026-10-31)

The current working tree contains Sprint/Scholar chat routing: frontend starts each newly opened chat in Sprint, sends mode with message/edit requests, and displays the selected mode description. Sprint checks SAP scope and calls the configured direct LLM provider fallback without retrieval, embeddings, or RAG; Scholar continues through the existing RAG handlers. Mode selection is UI state, so reopening any chat starts in Sprint. Added a Sprint source badge to satisfy TypeScript.

Verification: `backend/tests/test_chat_modes.py` passed (3 tests) under Python 3.14 with `HF_HUB_OFFLINE=true` and `DEBUG=false`; Python 3.12 `.venv` could not collect because FastAPI is absent there. Frontend tests passed (18); production build passed after the badge type fix; `git diff --check` passed. Runtime provider behavior was not exercised. Existing unrelated working-tree changes were preserved.

## Chat welcome mode descriptions (2026-10-31)

Moved Sprint and Scholar explanations from the fixed composer banner to selectable mode cards on the empty-chat welcome screen. The cards show which mode is active and switch the same chat mode as the composer toggle; the attachment/send area no longer has a mode-description panel.

Verification: frontend tests passed (18 tests); TypeScript and production build passed. `git diff --check` passed. An initial Vite bundle attempt hit a transient memory allocation failure; the immediate retry passed.

## Welcome page visual refinement (2026-10-31)

Refined the empty chat welcome view with compact Sprint/Scholar selectors, a restrained slate and teal palette, smaller icon and prompt cards, and a simple "Suggested questions" label. Removed the pulsing status indicator and unsupported "Verified SAP Intelligence" claim to keep the screen clear and credible.

Verification: frontend tests passed (18); TypeScript and production build passed; `git diff --check` passed.

## Welcome copy update (2026-10-31)

Updated the chat welcome heading to "Welcome to Clyptus AI" and supporting line to "Ask any question," above the mode selectors and SAP prompt suggestions. Frontend production build passed; `git diff --check` passed.

## Composer mode control refinement (2026-10-31)

Reduced the Sprint/Scholar toggle footprint beside the upload control and changed its active state to a restrained teal treatment with clearer compact typography.

Verification: frontend tests passed (18); TypeScript and production build passed; `git diff --check` passed.

## Company logo color reference (2026-10-31)

Saved the visual brand palette in `PROJECT_CONTEXT.md`: logo orange `#FF6600` (sampled from `company-logo.png`), white, and black/charcoal, with slate neutrals. Replaced teal highlights in the chat mode selector and welcome screen with the logo orange. Keep this palette for later UI work.

Verification: frontend tests passed (18); TypeScript and production build passed; `git diff --check` passed.

## SAP 72 welcome typography (2026-10-31)

Added SAP 72 Regular, Semibold, and Bold WOFF2 files from SAP's theming-base-content repository and applied them only within the chat welcome screen. Font files include Apache 2.0 license and source notice; other application typography remains unchanged.

Verification: frontend tests passed (18); TypeScript and production build passed, with all three WOFF2 weights emitted as local assets; `git diff --check` passed.

## Tavily-only web search (2026-10-31)

Removed SearXNG and Siftdog code and configuration: Docker Compose services, provider adapters, extraction/crawl/site-map interfaces, settings and example variables, live/unit integration tests, and their setup/integration documentation. Search and image retrieval now use Tavily only; empty or unavailable Tavily results produce no external evidence. No DuckDuckGo scraping fallback remains. Actual `.env` files were not read or edited. Docker containers were not inspected or stopped because this session cannot access the Docker Engine; old container status is unverified.

Verification passed: Tavily provider, web evidence, Tavily image, provider fallback, RAG generation unavailable, and audit RAG selections (35 tests total); Python 3.14 compileall; docker compose config --quiet; and git diff --check. Tests used HF_HUB_OFFLINE=true, DEBUG=false, a fake _test database URL, and a BaseSettings wrapper setting _env_file=None; no real DB/provider was contacted. The Docker CLI emitted a local config-file access warning, but Compose config validation exited successfully. Tavily API credentials and live service behavior were not exercised.

## Production-quality review and test pass (2026-10-31)

Reviewed the current implementation and tests without opening either `.env` file. The worktree already contained substantial owner changes; preserve them. Removed two unused catch bindings and five unused Markdown node bindings in `frontend/public/theme-init.js`, `frontend/src/components/chat/ChatMessage.tsx`, and `frontend/src/pages/DocumentManagementPage.tsx`. Updated `backend/tests/test_document_management_dashboard.py` to expect the stable `DOCUMENT_PROCESSING_FAILED` response instead of parser internals, consistent with generic document-error handling.

Verification: frontend Vitest 18 passed; production TypeScript/Vite build passed; `npm run lint` completed with 22 React/style warnings remaining; backend `compileall` passed; Compose config validation exited 0 with Docker config-access warnings; `git diff --check` passed. Focused backend dashboard/generic-error tests passed (4). Python 3.12 `.venv` collection is blocked because FastAPI, PyMuPDF, and JWT dependencies are missing. Used global Python 3.14.4 for broader backend checks. `pip check` on that global interpreter reports conflicts from unrelated installed packages; Ruff is not installed.

The non-live backend suite contains 476 collected tests (7 live deselected). The completed `--maxfail=1` broad run, additionally excluding two long real-corpus tests, stopped after 226 passed with one failure: `test_integration_real_retriever_and_chunk_uuids` retrieves a SOM chunk scored 0.5425 for a CI question; packing correctly rejects it below `RETRIEVAL_CALIBRATED_THRESHOLD=0.6761`. This is a real-corpus retrieval-quality issue or a corpus-specific integration expectation and needs investigation; do not lower the grounding threshold just to satisfy the test. Another legacy dashboard expectation was corrected and its focused regression passed. Full backend verification remains incomplete: the real-corpus tests `test_15_graceful_operation_empty_history` and `test_rag_query_with_attached_document` each ran for multiple minutes without completion and were interrupted. Conversation-memory tests excluding the first slow case passed (18); BP block regression passed (12). Provider credentials/live Tavily behavior, production backups, and deployment networking remain unverified.

Next: investigate why the real CI query retrieves SOM evidence and make the integration fixture deterministic while retaining the low-evidence fail-closed behavior. Add offline fixtures or explicit time bounds to real RAG tests so the non-live suite cannot call unbounded model/retrieval paths. Ensure the supported Python 3.12 environment is provisioned from backend requirements before deployment verification. Continue the remaining production actions and blockers recorded in `KNOWN_ISSUES.md` and `HUMAN_ACTIONS.md`.

## RAG hot-path loop cleanup and latency review (2026-10-31)

Reviewed the Scholar RAG pipeline for redundant loops and latency. Removed three output-identical redundant loops in `grounding_service.py`, `retrieval_service.py`, and `rag_service._retrieve_aspect_evidence`; added `backend/tests/test_rag_hot_path_loops.py` (4 passed). An old-vs-new equivalence harness (scratchpad only, not committed) showed identical results. The structural latency causes are recorded as `PERF-001` in `KNOWN_ISSUES.md`. No changes were committed; existing owner edits were preserved.

Unused code noted but not removed (needs owner decision): `reranking_service.compare_and_select` and `rerank` have no callers; `grounded_generator_service.py` and `context_packing_service.py` are used only by tests and `backend/scripts/run_real_samples.py`, not the app; `llm_service.generate_with_primary_model` (with a fixed 2 s sleep) is used only by `backend/evaluation/run_full_dev_baseline.py`; `RAGService.query` falls back to a `MagicMock` session in production code; the streaming memory branches repeat word-by-word token loops instead of `_verified_token_events`.

Unverified: live provider/Tavily latency, real-corpus timings (benchmarks used synthetic chunks on a loaded host), and DB-backed tests (no PostgreSQL listener). Next: instrument per-stage timings on a live request before changing thresholds, timeouts, or model lists.

## Sprint conversation memory (2026-10-31)

Sprint now uses conversation memory while still never loading the embedding model or calling retrieval. `messages._sprint_memory` classifies the memory intent: first/last-question lookups are answered verbatim from the database (`conversation_memory_service.exact_lookup_answer`, excluding the current message); history, mixed, and cross-conversation recall use `search_history(..., use_embeddings=False)` (keyword scoring only); the chat's rolling summary is passed to the Sprint prompt. Recall questions bypass the SAP-only scope refusal, and the Sprint system prompt allows answering from conversation context. Sprint turns now update the rolling summary (sync and streaming). Sprint messages are still stored without embeddings, so Scholar's semantic recall finds them only by keywords. Also fixed: the synchronous Sprint refusal lacked `grounding_score`, which `send_message` reads when persisting. Scholar's `rag_service` still has its own copy of the first/last lookup text; it could reuse `exact_lookup_answer`.

Verification: `test_sprint_conversation_memory.py` (8) plus `test_chat_modes.py` (3) passed. The wider selection passed 93; 2 failures and 22 errors were all PostgreSQL connection errors (no DB listener), including the DB-backed `test_conversation_memory.py` suite, so the new `get_first_user_message` exclusion filter and summary updates for Sprint are not verified against a real database. No frontend change: `conversation_memory` is not in the frontend source-type union, the same as for existing Scholar memory answers. Nothing committed.

## Landing page, colour system and welcome screen (2026-11-01)

Rewrote public copy so it matches the code: landing page, FAQ, Features, How-it-works and two login-page lines. Removed false claims (cross-encoder reranking, "<250ms neural rerank", "100% grounded citations", "zero hallucination", citations on every answer) and the login page's backend stack disclosure. Added a Sprint/Scholar section. Example T-codes that could not be verified were replaced with questions that ask for the transaction instead.

Unified colours on the logo orange `#FF6600`: see the colour-system notes in `PROJECT_CONTEXT.md`. Primary orange buttons now use charcoal text (white on `#FF6600` fails AA); this is a visible change from the previous white text. Rebuilt the chat welcome screen (data in `components/chat/welcomeContent.ts`) and changed the subtitle from "Ask any question" to an SAP-scoped line, because Sprint and Scholar refuse non-SAP questions. The heading "Welcome to Clyptus AI" was kept as the owner chose it, although other pages use "Clyptus.AI" and the footer/meta use "Clyptusap.ai"; brand naming is an owner decision.

Verification: Vitest 23 passed; production build passed; `git diff --check` passed; headless Chrome screenshots reviewed (dark/light landing, welcome screen in both modes). Not verified: real phone widths below about 526px (headless Chrome minimum window width), the authenticated chat page with the composer, and the admin pages after the global colour remap. The remap also touched sidebar and app-shell rules in `index.css`; check them visually in both themes before release. Nothing committed.

## Public nav: Sign in / Sign up (2026-11-01)

The landing nav now shows a plain logo and two actions: Sign in (`/login?mode=login`) and Sign up (`/login?mode=register`, the Create Account tab of `LoginPage`). Blocker for sign-up: the backend keeps public registration off by default (`REGISTRATION_ENABLED=false`, audit F-01), so the form returns "Self-registration is disabled. Ask an administrator for an account." until an owner enables it (optionally with `INVITE_CODE`). Not changed here because it is a security decision. `pages/RegisterPage.tsx` is unused and outdated (6-character password minimum, no route); delete it or route it after an owner decision. Verified with Vitest (27 passed), build, and screenshots; nothing committed.

## Sign-in page split layout (2026-11-01)

The sign-in page now has a brand panel on the left and the form on the right. No official company photo exists in the repo, so the left panel uses the official logo plus a brand SVG (`frontend/src/assets/login-visual.svg`); swap the `loginVisual` import in `LoginPage.tsx` to use a real photo. "Create an organisation" is a disabled placeholder under the form: the owner will specify its behaviour next (expected to need backend support: organisation model, admin/owner role, invites). Remove `disabled` and the "Coming soon" badge when it is wired up, and update `LoginPage.test.tsx`. Nothing committed.

## Sign-in page refresh (2026-11-01)

Sign-in now uses one landing-style canvas, a frozen form column on desktop, and a shield-plus-quotation in place of the session notice; details in `CHANGELOG_ENGINEERING.md`. The quotation makes two claims, both true of the current code: chats are private to the account unless shared, and Scholar verifies answers before display. Revisit it if sharing or verification behaviour changes. The existing `set-state-in-effect` lint warning for the `?mode=` sync in `LoginPage.tsx` remains. `OnboardingPage` still uses the older `login-layout`/`login-safe` styles.

## Organisation Portal (2026-11-01)

Implemented and verified (uncommitted); contract and implementation notes in `docs/ORGANISATION_PORTAL.md`, results in `CHANGELOG_ENGINEERING.md`.

Important: the owner's dev server (`uvicorn ... --reload` on port 8000) reloaded the new backend code and, because `AUTO_MIGRATE` defaults to true, migrated the real `sap_brim_ai` database to `0006_organisations`. The migration is additive; a read-only check after it found 0 organisations, codes or shared answers (no test data leaked) and all 4 users as active individual accounts without forced password changes. Downgrade path exists in the revision but was not run. Consider `AUTO_MIGRATE=false` for the dev server while backend schema work is in progress.

Environment: this host has about 1.5-2 GB free RAM. Under load the Docker VM restarted twice mid-test (Postgres "server closed the connection"), OpenBLAS failed to allocate in a subprocess, Python 3.14 hit access violations when many test files ran in one process, and Vitest workers timed out. Run backend tests one file per process with `OPENBLAS_NUM_THREADS=1`, and Vitest with `--maxWorkers=1`. Every such failure passed on a clean rerun.

Open follow-ups: e-mail delivery for activation codes and member invitations (currently shown once for manual hand-over); ownership transfer; rate limits are per process unless `REDIS_URL` is set; `_guard_login`/`/auth/login` failure audit rows still store full e-mail addresses (pre-existing; org login stores a fingerprint); the Agentic AI chatbot is marketing copy only. Not verified in a real browser session: modal focus trapping and clipboard fallbacks; widths below about 526px.

## Sprint small talk (2026-11-01)

Sprint no longer refuses greetings, thanks, feelings and identity questions. `messages._sprint_route` (shared by sync and streaming Sprint) orders memory answer → SAP answer → small talk → refusal. Small talk only applies when the turn would otherwise be refused, has no attachments, and `query_router` returns EMOTIONAL_CASUAL; the reply comes from the existing casual presets/LLM path with `SPRINT_CASUAL_SYSTEM_PROMPT`, source type `conversational`. Scholar's casual path is unchanged (the new `system_prompt` parameter defaults to its old prompt). Details and test counts in `CHANGELOG_ENGINEERING.md`.

Owner decisions noted, not changed: (1) in a chat that already has SAP questions, "hi"/"thanks"/"who are you?" still go to the Sprint SAP prompt (previous behaviour), because putting small talk first would hijack follow-ups such as "ok, what about dunning?"; (2) the shared router also counts "tell me a joke" and "write a poem" as casual, so Sprint now answers those in one sentence, as Scholar already did; (3) the shared preset for "who are you?" says "Clyptus.AI, your dedicated SAP BRIM Solution Architect and Assistant", while LLM-written identity replies say "Clyptus.AI Sprint".

Unverified: live provider replies to `SPRINT_CASUAL_SYSTEM_PROMPT` (tests stub the provider); DB-backed suites (`test_query_router` fixtures, `test_edit_prompt`, `test_followup_and_greetings::test_conversational_rag_service_flow`, `test_sap_restriction::test_rag_endpoint_refusal`, `test_audit_partial`) errored only because PostgreSQL was not running. Rerun them with the test DB up. Nothing committed.

## Scholar latency fixes (2026-11-01)

Measured a live Scholar request stage by stage (test DB, configured providers) before changing anything; see `KNOWN_ISSUES.md` PERF-001 for numbers. Fixed, behaviour-preserving: the retrieval index (about 10 s for 31k chunks) is built in a background thread at startup and 5 s after `invalidate_cache()` (`RETRIEVAL_CACHE_WARMUP`); the multi-source comparator searches question parts concurrently (max 4); `model_cooldowns` in `llm_service` skips models after a 404/decommissioned (1 h), a 429 (retry-after, else 30 s) or a timeout (60 s), in all provider loops, the style classifier and the query rewriter (now `max_retries=0`, 10 s timeout). Live after: first question after startup 16.8 s to 9.6 s, typical 6.2 s to 5.2 s, 6-part web stage 27.4 s to 8.6 s.

Owner decisions (not changed; `.env` not edited): (1) `MULTI_SOURCE_COMPARE_ENABLED=true` and `REPO_SOURCE_ENABLED=true` in the local `.env` make every Scholar question run Tavily (2.5-4.8 s per part) even when the knowledge base matches at 0.92-0.98, and web evidence won both measured comparisons; the default `false` keeps web search for weak evidence only. (2) `LLM_MODEL=llama-3.3-70b-versatile` returns 404 for this Groq key; set a working model. (3) Groq free-tier per-minute token limits push large prompts (incident/design answers) to Gemini, 25-34 s per call; the grounding repair pass regenerates the whole answer (+25 s when it triggers). (4) `HF_HUB_OFFLINE=1` would save about 5 s of startup once the embedding model is cached.

Verification: `test_scholar_latency.py` 14 passed; full non-live suite per file 564 passed / 12 failed / 2 skipped, all 12 explained in `CHANGELOG_ENGINEERING.md` (none from these changes; the 2 comparator failures reproduce on HEAD's file). Pre-existing test drift to resolve: `test_query_router` expects `direct_llm` for greetings, the code returns `conversational`; `test_repo_retrieval_and_comparison` KB-vs-repo winner tests. I started the `sap_assistant_postgres` container for the measurements and stopped it afterwards. Nothing committed.

## One .env file (2026-11-02)

The project now has a single settings file, the repository-root `.env` (template `.env.example`), read by Docker Compose and by `backend/app/config.py`. The local `backend/.env` was merged into it without printing values and deleted; 17 dead SearXNG/Siftdog/`SEARCH_*` keys were dropped. Backups of both originals are the git-ignored `.env.bak` and `backend/.env.bak`: delete them once the owner has started the backend and Compose successfully. `backend/.env.example` was merged into `.env.example` and deleted (a tracked deletion). Details and verification in `CHANGELOG_ENGINEERING.md`.

Verified: all 133 declared settings fields are unchanged; `docker compose config` output is byte-identical; `test_single_env_file.py` (6) and the startup/database-URL tests (5) passed under Python 3.14. Not verified: an actual backend start or `docker compose up` with the merged file (both are config-equivalent by the checks above). Other checkouts or teammates that still have `backend/.env` must move its keys into the root `.env`; the backend no longer reads it. The backend now also loads the Compose-only keys (`POSTGRES_PASSWORD`, `SAP_BRIM_DB_PASSWORD`, ...) as unused `Settings` extras (`extra="allow"`); nothing serializes settings today, but keep it that way. Nothing committed.

## SETUP.md, README rewrite and push to main (2026-11-02)

Added `SETUP.md` (single setup/deployment/troubleshooting guide) and rewrote `README.md` from the implementation; `docker.md` holds backup/restore; `docker-setup/README.md` points to `SETUP.md`. Fixed `backend/requirements.txt` (alembic, PyJWT, PyMuPDF, google-generativeai, python-docx, email-validator were imported but missing), completed `.env.example`, extended `.gitignore`. Details and verification in `CHANGELOG_ENGINEERING.md`; new issues SETUP-001, FE-001 and API-001 in `KNOWN_ISSUES.md`.

Pushed to `origin/main` (Clyptus-Soft/SAP_BRIM_Ai, private) as a fast-forward after merging `origin/main` into `audit-fixes`; this also published the 54 earlier local `audit-fixes` commits. `AUDIT_REPORT.md` (root, untracked, open security findings) was deliberately not committed. The knowledge-base PDFs were already on the remote (`SE-updated-rag-kb`, identical blobs); their licensing decision (`HUMAN_ACTIONS.md` §3) is still open.

Blockers and environment notes (SETUP.md session): drive C: was full (about 130 MB free) during this session; the fresh-install check ran on D: and its folder `D:\claude-setup-check` (venv, pip cache) was left for the owner to delete because the removal needs human approval. The project `.venv` (Python 3.12) now has the full backend requirements installed. I restarted the `sap_assistant_postgres` container for tests and stopped it again afterwards. Fresh installs need document tiers set before Scholar retrieves anything (SETUP-001). Unverified: `docker compose up` on a brand-new volume, `ingest.py` on a fresh database (not run: it would re-embed the real corpus), and a production deployment.

## Scholar fallback chain and the "couldn't generate a verified response" bug (2026-11-02)

Root cause: not a provider outage. All three LLM tiers work. The claim verifier rejected a generated answer, and the pipeline replaced it with the generic message (audit F-03 fail-closed rule); the web retry was skipped because web search had already run. Fixed in `rag_service.py`:
- a rejected answer has its unconfirmed, contradicted and critical claims removed and is published with a notice, never as `verified`;
- if no LLM tier answers, approved SAP web results become a linked `unverified` answer;
- only if that also fails does the user get `ALL_METHODS_UNAVAILABLE_RESPONSE`.

`llm_service.py` now skips a whole provider for an hour after a rejected key and logs which tier answered. Details: `RAG_FAILURE_DIAGNOSIS.md`, `DECISIONS.md`, `CHANGELOG_ENGINEERING.md`. Nothing committed.

Verified: `test_llm_web_fallback_chain.py` 19 passed; related RAG/LLM files pass except the 7 explained failures in `CHANGELOG_ENGINEERING.md` (none caused by this change); frontend tsc/Vitest 77/build passed. Live runs against `sap_brim_ai_test` covered:
- the reported question;
- the complex components question;
- forced Groq outage (Gemini answered) and forced Groq+Gemini outage (OpenRouter answered);
- forced all-tier outage (live Tavily answer with links);
- forced gate rejection (published `partial` with the note).

Owner actions and open points:
1. Set `LLM_MODEL` in `.env` to a model the Groq key can use (`llama-3.3-70b-versatile` 404s); `gemini-3.8-flash` is over quota (`KNOWN_ISSUES.md` LLM-002).
2. Policy change to confirm: F-03 "unverified drafts are never shown" no longer holds for Scholar. Rejected answers are shown with a note. Landing and How-it-works copy was adjusted; other marketing lines still say "verified answer" broadly (FAQ, AssistantGuideModal, login visual) and may need review.
3. Answer quality, separate from this bug: with `MULTI_SOURCE_COMPARE_ENABLED=true` the comparator often picks thin web passages over richer knowledge-base chunks. The complex components answer was verified but listed components without their functions.
4. Sprint is unchanged: it has no web fallback and still uses `UNAVAILABLE_RESPONSE` when no tier answers.
5. No whole-request generation deadline (LLM-003). Uptime-dependent test bug TEST-002.

Environment: commit memory on this host dropped to about 0.4-1.7 GB free and C: had 0.2-2.7 GB free. The first repro hit `MemoryError`; the `sap_assistant_postgres` container exited (code 0) mid-run and was restarted, and it is left running as it was at session start. Blank keys for tests with bash `env VAR=` (PowerShell `$env:VAR=''` deletes the variable, so the real `.env` keys load).
