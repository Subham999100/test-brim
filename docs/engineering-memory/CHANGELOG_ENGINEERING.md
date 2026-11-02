## 2026-11-02 - SETUP.md, README rewrite, dependency fixes, push to main

* Docs: new root `SETUP.md` (prerequisites, `.env` values to change with a placeholder example, Compose, venv, Alembic, startup, knowledge-base ingestion and source tiers, frontend, sign-in/org onboarding, tests, Docker reference, server deployment, troubleshooting). `README.md` rewritten from the implementation (three explorer reports, spot-checked against code): removed false claims (cross-encoder reranking, "no migration framework", SearXNG ports, pasted session notes, share page "never the answer"). `docker.md` now holds the backup/restore procedure that used to be README section G; image name corrected to `pgvector/pgvector:pg16`. `docker-setup/README.md` points to `SETUP.md`. All relative links/anchors checked.
* `backend/requirements.txt`: added `alembic`, `PyJWT`, `PyMuPDF`, `google-generativeai`, `python-docx` and `pydantic[email]` (email-validator); all are imported by the app but were missing, so a clean install could not start the backend (AUDIT_REPORT F-28). `python-jose` left in place (unused).
* `.env.example`: corrected the `LLM_PROVIDER` comment (no `openai`/`local` providers; `local` = no preferred provider), added `AUTO_MIGRATE`, `REGISTRATION_ENABLED`, `INVITE_CODE`, `DEFAULT_ACCESS_GROUP`, `RATE_LIMIT_ENABLED`, `REDIS_URL`, `TRUSTED_PROXIES`, `INCLUDE_SELF_AUTHORED_DOCS` (all at code defaults) and an `EMBEDDING_MODEL` warning. `.gitignore`: dumps, logs, tool caches, editor/OS files.
* `database.py`: example port in the missing-`DATABASE_URL` message corrected to 5434.
* New known issues: SETUP-001 (fresh installs retrieve nothing until tiers are set), FE-001 (hard-coded API URL), API-001 (smaller inconsistencies).
* Verification of SETUP.md: a brand-new Python 3.12 venv installed only from `backend/requirements.txt` (on D:, C: was full) passed `pip check`, imported the app (76 OpenAPI operations) and ran `alembic heads`; the SETUP §4.4 example `.env` with generated secrets passes `security_settings_errors` and `docker compose config`; `.env.example` unedited fails only on `JWT_SECRET`; `alembic current` on the dev DB = `0006_organisations (head)`; uvicorn started as documented (port 8765, `_test` DB) served `/health` `{"status":"healthy","database":{"status":"connected"}}`, `/docs`, 76 operations, 401 without a token; Vite dev server served the app (HTTP 200); all doc links/anchors resolve.
* Tests (Python 3.12 `.venv`, one file per process, provider/search keys blanked, `WEB_FALLBACK_ENABLED=false`, `sap_brim_ai_test`): 64 files, 570 passed, 12 failed, 2 skipped, 7 live deselected. The 12 match the previously documented set: 2 need a real LLM; 2 Tavily image tests need web fallback on; 3 assert defaults the local `.env` overrides (all 5 pass with template defaults); 3 `test_query_router` expect `direct_llm` while committed `rag_service` returns `conversational`; 2 comparator tests fail identically on HEAD (checked in a HEAD worktree). Frontend: Vitest 77/77, `npm run build` passed, lint warnings only.

## 2026-11-02 - One .env file

* Why there were two: Docker Compose reads `.env` next to `docker-compose.yml` (repository root) for `${POSTGRES_*}`/`${SAP_BRIM_DB_PASSWORD}` substitution, while `config.py` preferred `backend/.env` (then `backend/app/.env`, then root). Both files had to carry the same app password and port.
* Changed: `Settings.model_config.env_file` is now only `ROOT_DIR / ".env"`. The local `backend/.env` was merged into the root `.env` by a scratchpad script that never printed values (36 live keys, values byte-identical); 17 dead SearXNG/Siftdog/`SEARCH_*` keys were dropped. Originals kept as git-ignored `.env.bak` and `backend/.env.bak`. `backend/.env.example` merged verbatim into root `.env.example` (Compose section + Backend section) and deleted; the stray literal `\n` line at the end of the old root template removed. Messages in `database.py`, `main.py`, `alembic.ini`, `migrate_sqlite_to_pgvector.py`, `docker-compose.yml` and README/`docker.md`/`docker-setup/README.md` now name the root `.env`.
* Verification: all 133 declared `Settings` fields equal when loaded from `backend/.env.bak` and from the new `.env` (compared by name, values not printed); `docker compose config` output hash identical before and after; `docker compose config --quiet` exit 0. New `test_single_env_file.py` 6 passed; `test_missing_database_url_is_rejected`, `test_published_or_weak_secrets_are_reported`, `test_f40_startup_rejects_non_hmac_jwt_algorithm` 5 passed (Python 3.14; the 3.12 `.venv` lacks FastAPI/Alembic). `py_compile` and `git diff --check` passed.

## 2026-11-01 - Scholar latency: measured and fixed (uncommitted)

* Measured with live providers against `sap_brim_ai_test` (stage timers in a scratchpad harness, no prompts or secrets printed); numbers in `KNOWN_ISSUES.md` PERF-001.
* Changed: `retrieval_service.warm_cache`/`schedule_warm_up` build the chunk index in a daemon thread; the app lifespan schedules it at startup and `invalidate_cache()` reschedules it 5 s after the last invalidation (`RETRIEVAL_CACHE_WARMUP`, default true, off in `conftest.py`). `MultiSourceComparator._search_web_parts` runs per-part web searches concurrently (at most 4), keeps part order, and a failed part yields no results instead of dropping the parts after it. `llm_service.ModelCooldowns` (`model_cooldowns`) is consulted by every Groq/Gemini/OpenRouter loop (sync and streaming), the answer-style classifier and the query rewriter; request-specific errors (400 context, 413, 5xx) are not remembered. The query rewriter's Groq client uses `max_retries=0` and a 10 s timeout. `conftest.py` clears cooldowns around each test.
* Verification: `test_scholar_latency.py` 14 passed (9 failed before implementation, for the expected reasons). Full non-live suite, one file per process against the test DB with provider keys blanked: 63 files, 564 passed, 12 failed, 2 skipped. All 12 checked: 2 need a real LLM (fail closed with `unavailable`), 3 `test_query_router` tests expect `direct_llm` where committed `rag_service` returns `conversational`, 2 comparator tests fail identically on HEAD's `multi_source_compare.py`, 2 assert flag defaults that the local `.env` enables, 1 assumes a tighter `GROQ_TOKENS_PER_MINUTE`, and 2 Tavily image tests pass (4/4) without the harness's `WEB_FALLBACK_ENABLED=false`. Live after: first question after startup 16.8 s to 9.6 s, typical question 6.2 s to 5.2 s, 6-part web stage 27.4 s to 8.6 s.

## 2026-11-01 - Sprint small talk (uncommitted)

* Changed: Sprint answers greetings, thanks, feelings and identity questions ("hi", "who are you?", "what is your name?", "I had a bad day") instead of returning the SAP-only refusal. New `messages._sprint_route` decides each Sprint turn for both the sync and streaming paths: memory answer → SAP answer (including SAP follow-ups via history) → small talk → refusal. Small talk is only considered when the turn would otherwise be refused, there are no attachments, and `query_router` (the same router as Scholar's casual path) returns EMOTIONAL_CASUAL. Replies reuse the existing presets and `generate/stream_emotional_casual_reply`, now with an optional `system_prompt` (default unchanged, so Scholar is unaffected); Sprint passes the new `SPRINT_CASUAL_SYSTEM_PROMPT` (casual rules + Clyptus.AI Sprint identity, no other-model claims, SAP-only scope). Stored with source type `conversational`, which the frontend already renders. No retrieval, embeddings or frontend changes.
* Verification: `test_sprint_small_talk.py` 11 passed (6 failed before the change for the expected reason: refusal returned); with `test_chat_modes.py` and `test_sprint_conversation_memory.py`, 22 passed. Related files, one per process, offline with a fake `_test` DB URL and blank provider keys: `test_audit_rag_pipeline` 10, `test_bp_block_regression` 12, `test_query_router` 19 passed / 9 errors, `test_followup_and_greetings` 6 passed / 1 failed, `test_sap_restriction` 2 passed / 1 failed, `test_audit_partial` 2 passed / 3 errors, `test_edit_prompt` 2 failed. Every failure and error was a PostgreSQL connection refusal (no DB listener on 5434). `py_compile` and `git diff --check` passed.

## 2026-11-01 - Organisation Portal (uncommitted)

* Added: multi-tenant organisations per `docs/ORGANISATION_PORTAL.md`. Backend: Alembic `0006_organisations` (organizations, org_activation_codes, org_shared_answers, org_answer_likes, org_answer_comments; users gain account_type, organization_id, org_role, is_active, must_change_password, last_login_at), Super-Admin-issued single-use activation codes (80-bit `secrets`, SHA-256 stored, 72 h TTL, row-locked activation, rate-limited, generic errors, audited), organisation sign-in separate from individual sign-in, server-enforced forced password change, inactive/suspended accounts rejected at token validation, org member/admin/Super Admin endpoints, deterministic SAP BRIM topic categoriser. Frontend: `/organisation` portal (benefits, how it works, hub preview, "Coming soon: Secure Agentic AI Chatbot", request form), `/organisation/login`, `/organisation/activate`, `/organisation/change-password`, `/app/organisation` Knowledge Hub, `/app/organisation/admin` dashboard, "Share to organisation" in chat, sidebar Organisation item, Super Admin "Organisations" and "Individual users" tabs.
* Integration fixes after review: owner self-deletion blocked (409); troubleshooting categoriser broadened ("no ... was created", "wasn't ... posted", "missing", "what should I check"); Markdown stripped from hub card previews; hub header icon alignment; Super Admin tab bar wraps; decorative security note uses brand orange.
* Verification: backend organisation tests 65 passed (categoriser 35 after additions, activation 13, knowledge 6, accounts/admin 18); existing auth/security/privacy/access/audit/chat/migration suites 78 passed, run one file per process. Frontend Vitest 77 passed (`--maxWorkers=1`), build passed, no new lint warnings. End-to-end over HTTP against a scratch backend bound to `sap_brim_ai_test`: 40/40 checks (request → approval → activation → member → forced password change → like → share → likes/comments → cross-org isolation → suspend/reactivate). Signed-in screens screenshotted in both themes. E2E data removed from the test database.

## 2026-11-01 - Sign-in page: one canvas, frozen form, security quote (uncommitted)

* Changed: the sign-in page is one continuous canvas in the landing palette (theme tokens and orange glow across both columns; no separate dark panel). On desktop the page is locked to the viewport and the form column scrolls internally only when the window is very short. The illustration is now an inline, theme-aware SVG component (`components/auth/LoginVisual.tsx`; the static `assets/login-visual.svg` was removed). The old "Signed, short-lived sessions" note was replaced by a shield icon and a quotation on the left. Form upgrades: linked labels, `autocomplete` hints (username/current-password vs email/new-password), show/hide password toggle, tab semantics on the Sign In / Create Account switch, `role="alert"` errors, per-mode headings and page title, and the backend password rule (12-72 characters) enforced and shown when creating an account.
* Verification: Vitest 33 passed (5 in `LoginPage.test.tsx`); build passed; screenshots of sign-in in dark and light, Create Account at 1440x800 (fits without page scroll), and a narrow width.

## 2026-11-01 - Split sign-in page and Create organisation placeholder (uncommitted)

* Changed: `LoginPage` is a two-column layout (`auth-*` classes in `index.css`): a charcoal brand panel on the left (white logo, `assets/login-visual.svg` illustration of SOM → CC → CI → FI-CA feeding a verified answer, short tagline) and the existing sign-in/create-account form on the right. Below 900px only the form shows, with the logo above it. The submit button is now the brand orange button (the dark button was nearly invisible in dark mode). A disabled "Create an organisation" button with a "Coming soon" badge sits below the form; its behaviour is not implemented yet. `OnboardingPage` still uses the old `login-layout` classes and is unchanged.
* Verification: Vitest 32 passed (4 new in `LoginPage.test.tsx`: panel order, organisation option placement and disabled state, tab per `mode`); build passed; screenshots in light/dark, both tabs, and a narrow width.

## 2026-11-01 - Bold nav labels and shining logo (uncommitted)

* Changed: public nav links, Sign in and Sign up are bold (nav links 12px to 13px). `BrandLogo` gained a `shine` prop, used in `PublicNav`: an orange drop-shadow glow plus a glint that sweeps across the logo every 5 seconds, masked by the logo image so no box appears. Both logo files share one alpha shape, so one mask serves light and dark themes. The global reduced-motion rule leaves only the static glow.
* Verification: Vitest 28 passed (shine test added to `PublicNav.test.tsx`); build and lint clean; headless captures with the glint frozen mid-sweep (both themes) and sampled live (sweep visible at 1.7s, at rest otherwise). Temporary probe pages and scratch dev servers were removed.

## 2026-11-01 - Public nav: plain logo, Sign in / Sign up (uncommitted)

* Changed: the public nav shows the logo without the boxed, glowing "button" treatment (the `highlighted` BrandLogo variant and its `.brand-highlighted` CSS were removed; nothing else used them). "Try now" is replaced by "Sign up", linking to `/login?mode=register` (Create Account tab); "Sign in" links to `/login?mode=login`, desktop and mobile.
* Verification: Vitest 27 passed (4 new in `PublicNav.test.tsx`); build and oxlint clean for the nav files; headless screenshots of the nav (dark/light) and of `/login?mode=register` opening the Create Account tab.

## 2026-11-01 - Landing copy accuracy, brand colour system, welcome screen (uncommitted)

* Changed: landing, FAQ, Features, How-it-works and login copy now matches the implementation (Sprint vs Scholar, dense + BM25 + identifier retrieval with reciprocal rank fusion, multi-signal reranking, claim-level verification, fail-closed, approved SAP web fallback, admin-only citations); removed the cross-encoder, "<250ms rerank", "100% grounded", "zero hallucination" and per-answer-citation claims, plus backend stack names on the login page. Added a Sprint/Scholar section; quotes in the boundary examples now use the real refusal and unavailable messages. Unified the palette: one `#FF6600` ramp for Tailwind `orange`/`brand`/`sap`, CSS tokens for light and dark, warm/olive greys and terracotta accents remapped to slate and the brand ramp (159 colours, 340 replacements; error reds and status colours kept), charcoal text on primary orange buttons for AA contrast, and landing labels raised from 6-10px to 10-14px. Rebuilt the chat welcome screen: SAP-scoped subtitle (replacing "Ask any question"), mode cards explaining speed and verification trade-offs, per-mode suggested prompts, attachment hint and an AI-accuracy notice; removed dead legacy welcome CSS whose unlayered rules overrode Tailwind (8px text).
* Verification: Vitest 23 passed (5 new in `WelcomeScreen.test.tsx`); TypeScript and production build passed; oxlint warnings only in existing `DocumentManagementPage.tsx`; `git diff --check` passed. Headless Chrome screenshots of the landing page (dark and light) and the welcome screen (dark/light, Sprint/Scholar, about 526px minimum layout width) checked visually, using temporary harness files that were deleted afterwards.

## 2026-10-31 - Sprint conversation memory (uncommitted)

* Changed: Sprint answers first/last-question lookups from the database, recalls earlier messages (this chat or other chats) by keyword search without embeddings, sends the rolling summary to the LLM, and updates that summary after each turn. Memory questions bypass the SAP-only refusal. `search_history` gained `use_embeddings`; `get_first_user_message` gained `exclude_message_id`; new `exact_lookup_answer`. Fixed missing `grounding_score` on the synchronous Sprint refusal.
* Verification: `test_sprint_conversation_memory.py` 8 passed, `test_chat_modes.py` 3 passed; wider selection 93 passed, with failures/errors only from missing PostgreSQL. DB-backed memory tests not run.

## 2026-10-31 - RAG hot-path loop cleanup (uncommitted)

* Changed: `grounding_service.verify_answer` lowercases each passage once and scores every passage once per claim (the best-passage pick and supporting-source list previously ran two separate scoring loops); term regexes are compiled once via `_term_pattern`. `retrieval_service` caches lowercased chunk text (`text_lower`) at index build so BM25/coverage scoring no longer lowercases a chunk per query term. `rag_service._retrieve_aspect_evidence` uses an id set instead of a quadratic identity scan when guaranteeing per-aspect passages.
* Verification: old-vs-new equivalence harness produced identical outputs (120 grounding cases, 60 hybrid-search cases on a fake session). Alternating timing on a loaded host: hybrid search median 1,183 -> 907 ms/query at 12,400 synthetic chunks; verify_answer median 3,010 -> 2,270 ms for 90 claims x 16 passages. New `backend/tests/test_rag_hot_path_loops.py`: 4 passed. RAG/grounding/router selection: 91 passed; 2 failures and 13 errors are pre-existing (Groq token-budget expectation vs `GROQ_TOKENS_PER_MINUTE=20000`, and DB-dependent fixtures with no PostgreSQL); the restriction-endpoint failure was reproduced on the original code. `git diff --check` passed.

## 2026-10-29 - Upload bounds and source authority tiers (commits 0da1283, 80dda9a, c67b5e4, bedece9, 704e8fa, 12244f8)

* Changed: added chunked admin upload spooling and request-body limits, format signature checks, opt-in extended formats, and PDF page caps (F-20); parsed hostname boundary matching (F-52); persisted `documents.source_tier` with a conservative default, historical mapping backfill, audited admin classification, and retrieval/confidence propagation (F-53); excluded self-authored sources before ranking by default and removed misleading generator labels (F-08/F-54); added account export/deletion and dry-run attachment retention (F-31).
* Verification: upload/security/RAG selection: 72 passed; focused hostname/source-tier/migration/upload selection: 5 passed; changed modules compiled; `git diff --check` passed. Tests importing retrieval required Hugging Face offline mode.
* Verification: F-31 account privacy suite, including final-admin protection: 4 passed.
* Verification: self-authored exclusion, F-01 access groups, and generator-label tests: 3 passed; upload/process/classify/retrieve integration: 1 passed.
* Remaining: extraction timeout and F-21 daily/message/attachment budgets; F-52 still trusts upstream web license/gate fields; existing PDFs were not regenerated and orphan records were not purged; encrypted backup setup remains an owner/deployment task. See `NEXT_SESSION.md`.

# Engineering changelog

## 2026-10-28 — Portable Docker and local development setup guide

* Changed: added `docker-setup/README.md`; updated root `README.md` and `backend/.env.example` with current setup, authentication, environment, and CORS details; removed machine-specific paths.
* Reason: help new contributors start Docker dependencies and run the FastAPI/React app without relying on this workstation's paths or credentials.
* Verification: documentation references, Compose configuration, and whitespace checks recorded in the current handover.

## 2026-10-28 — Initial security audit remediation

* Changed: auth/demo paths, roles/provisioning, token expiry and revocation, extraction auth/size/type checks, direct RAG output filtering, in-process rate/body limits, admin processing SSE, share revocation, CORS/security headers, SearXNG secret configuration, and related frontend flows/tests.
* Reason: address high/critical behaviors identified in the audit characterization tests. `SECURITY_AUDIT_REPORT.md` was not available in this checkout.
* Verification: focused regression suites: 20 passed; frontend tests: 10 passed; Python compilation and frontend TypeScript/Vite build passed; `git diff --check` passed. npm advisory scan failed due to unreachable registry endpoint; Python audit scanner unavailable. Full backend suite and Postgres behavior not verified.
* Remaining: see SEC-001 in `KNOWN_ISSUES.md` and `NEXT_SESSION.md`.

## 2026-10-27 — Initial audit, route correctness, and handover memory

* Changed: `backend/app/services/query_router.py`, `backend/app/api/rag.py`, `backend/tests/test_query_router.py`; added `docs/engineering-memory/` and `AGENTS.md`.
* Reason: prevent retrieval bypass for SAP component comparisons; align streaming RAG chat authorization; establish persistent handover documentation.
* Verification: backend compilation passed; frontend build passed; direct route smoke checks passed; 41 focused tests collected; 16 parameterized router cases plus 1 stream ownership regression passed. Full focused pytest final result was not captured and is not claimed as passing.
* Migration/config impact: none from this audit change. The pre-existing message-embedding/chat-summary schema change still needs live DB migration verification.
* Remaining concern: memory summary completeness and full integration verification.

## 2026-10-27 — Watermarked conversation summary and isolated regression

* Changed: `conversation_memory_service.py`, `models/chat.py`, `database.py`; expanded memory/follow-up tests and added `test_memory_schema_migration.py`.
* Reason: process messages as they leave the 20-message window in stable order, avoid duplicate updates, and commit the summary with its progress watermark.
* Verification: focused isolated-PostgreSQL run — 54 passed, 2 deselected. The full non-live run crashed in Python 3.14 Torch/Transformers during corpus ingestion. After storage recovered, backend compilation and frontend build passed, as did a pure follow-up test (1 passed, 6 deselected).
* Migration/config impact: two nullable columns (`summary_through_created_at`, `summary_through_message_id`) added using existing additive runtime migration convention. Scratch-schema test verified idempotency and preserved existing data.
* Remaining concerns: summary is lossy and capped at 4,000 characters; migration system remains non-versioned; full suite and Docker test-container cleanup are blocked by the daemon metadata error.

## 2026-10-27 — Docker/PostgreSQL port alignment and Windows startup docs

* Changed: `docker-compose.yml`, `.env.example`, `backend/.env.example`, `README.md`, and `docker.md`.
* Reason: Compose defaults/examples were inconsistent at 5435 while the stopped PostgreSQL container was configured for host port 5434; setup documentation also named the wrong volume and offered stale SQLite fallback/restore instructions.
* Configuration: aligned defaults to `127.0.0.1:5434` -> `5432`; verified the data volume name `sap_brim_pgdata`; documented that app config expects role/database `sap_brim_ai`, but the actual database catalog could not be queried.
* Verification: `docker compose config --quiet` passed; rendered config resolved port 5434 and alternate fresh-project volume `sap_brim_fresh_pgdata`. `py -3.14 -m compileall -q backend` passed. `npm run build` passed (TypeScript + Vite 8.3.3).
* Blocker at that point: Docker reported a read-only internal container `hosts` path, missing `runc`, and containerd image blob I/O error. It was subsequently recovered; see the following entry.

## 2026-10-27 — Recover Docker Desktop WSL data disk and verify application

* Recovery: Docker Desktop logs showed WSL data-disk format failure (`mkfs` exit 1) and failure to detach `docker_data.vhdx`. Ran `wsl --shutdown` then `docker desktop start`; existing containers and `sap_brim_pgdata` resumed. No container or volume was deleted.
* Verification: `docker compose up -d postgres searxng siftdog` succeeded; PostgreSQL healthy and published on 5434; read-only SQL confirmed 62 documents and 12,406 chunks plus pgvector 0.8.7. Backend `/health` returned healthy. Frontend, Swagger, Siftdog health, and SearXNG returned HTTP 200.
* Remaining: no backup created; full regression suite not rerun. Existing `pg_isready` healthcheck uses `sap_assistant`, a role absent in this cluster, and does not verify authentication. App role `sap_brim_ai` works.

## 2026-10-27 — Adaptive RAG Answer Generation, Output Budget & Root-Cause Pipeline Fixes

* Changed:
  - `backend/app/services/answer_planner.py`: Added dedicated `production_incident` archetype with mandatory 10-section structure (Executive Summary, Problem Analysis, Evidence and Findings, Root-Cause Analysis, Step-by-Step Investigation, Corrective and Recovery Actions, Duplicate Prevention and Financial Integrity, Validation and Reconciliation, Risks and Limitations, Final Recommendations) while preserving solution-design and upgrade reconciliation archetypes.
  - `backend/app/services/answer_style_router.py`: Added `production_incident` to `AnswerType` and `DOMAIN_STRUCTURED_ARCHETYPES`. Configured up to 10 sections, detailed depth, procedural steps, and 10-section layout template. Updated `render_style_instructions` to enforce adaptive length (100–250 words simple, 400–800 words intermediate, 1,200–2,000 words complex incident target).
  - `backend/app/services/evidence_selection_service.py`: Fixed chunk starvation bug in `select_strongest_evidence` where evidence was rigidly sliced to `settings.RERANK_TOP_K` (4 chunks). Implemented dynamic budget scaling (`internal_top_k` up to 16 chunks) when queries contain multiple aspects.
  - `backend/app/services/rag_service.py`: Enhanced multi-aspect query generation in `scenario_aspects` to detect complex multi-component incidents (CC, CI, FI-CA, duplicate financial records, safe recovery, reconciliation matrix) and split queries into independent aspect searches. Added structured `diagnostics` logging and metadata to `process_query` and `stream_query`.
  - `backend/app/services/llm_service.py`: Updated `EVIDENCE_AWARE_ANSWER_INSTRUCTIONS` with explicit adaptive word targets. Increased evidence context budget to `(20, 24000)` for `production_incident`. Added finish reason detection (`finish_reason == "length"`), seamless continuation logic (`_continue_gemini`, `_continue_openrouter`), and token diagnostics tracking attributes.
  - `backend/tests/test_adaptive_rag_pipeline.py`: Added 10 automated regression tests covering Tests A–F (complex production incident, simple question brevity, insufficient evidence boundaries, multi-turn context retention, finish reason continuation and diagnostic tracking, existing behavior preservation).
* Verification:
  - `py -3.14 -m pytest backend/tests/test_adaptive_rag_pipeline.py -v`: 10 passed.
  - Full regression run: `backend/tests/test_adaptive_rag_pipeline.py`, `backend/tests/test_solution_design_answers.py`, `backend/tests/test_senior_upgrade_and_reconciliation.py`, `backend/tests/test_answer_style_router.py`, `backend/tests/test_sap_restriction.py`, `backend/tests/test_citation_provenance.py`, `backend/tests/test_security.py`: 80 passed in 7.03s.
  - `git diff --check`: 0 errors.

## 2026-10-28 — Branch Creation and Knowledge Base Ingestion to Remote

* Branch created: `SE-updated-rag-kb`
* Changed: `.gitignore` updated to track all knowledge base documents under `knowledge_base/documents/`.
* Code pushed: All adaptive RAG pipeline additions, conversation memory services, streaming authorization fixes, and test suites.
* Knowledge base pushed: All 61 PDF documents (~489 MB total) pushed in sequential size-managed batches directly to `origin/SE-updated-rag-kb` without hitting HTTP request timeouts or requiring LFS bandwidth quotas.
* Verification: `git status` clean; remote branch `origin/SE-updated-rag-kb` fully synchronized.

