# Audit fix log

Branch `audit-fixes` (from `security-remediation-20261028` @ `0f44c57`). Findings: `AUDIT_REPORT.md` F-01 – F-59.
Owner actions and product decisions: `HUMAN_ACTIONS.md`. API/config changes: `CHANGELOG_AUDIT.md`.

## Summary

Status after the current **Phase 3 partial** work; Phases 4–6 remain open.

| Status | Count |
|---|---|
| fixed | 18 (F-01, F-02, F-03, F-04, F-06, F-09, F-10, F-23, F-25, F-29, F-37, F-38, F-39, F-40, F-41, F-42, F-45, F-49) |
| partial | 6 (F-05, F-21, F-26, F-27, F-33, F-50) |
| skipped | 0 |
| needs-human | 1 (F-48: rotation and history rewrite listed in HUMAN_ACTIONS.md) |
| not started | 34 |

### Current session verification

| Check | Result |
|---|---|
| Backend full baseline `pytest -m "not live"` | Started with required blank provider keys; stalled at 34% in a CPU-heavy test for several minutes and was interrupted. No final baseline result available. |
| Focused security/provider/RAG tests | 62 passed: `test_llm_egress_controls.py`, `test_prompt_security_filters.py`, `test_adaptive_rag_pipeline.py`, `test_followup_and_greetings.py`, and `test_answer_style_router.py`. |
| `ruff check backend/app backend/migrations --select F,E9` | Not run: `ruff` executable is not installed/on PATH in this environment. |
| Frontend oxlint | Passed with existing warnings after F-45 hook-order fix; no rules-of-hooks errors. |
| Frontend TypeScript check | Completed with no diagnostics. |

### Verification before and after

Environment for backend tests: PostgreSQL 16 + pgvector in Docker, database `sap_brim_ai_test` only
(the `conftest.py` guard refuses any database not ending in `_test`). LLM, search and vision keys blanked
and `WEB_FALLBACK_ENABLED=false`, so no external calls; `-m "not live"`.

| Check | Baseline (before any change) | After Phase 1 | After Phase 2 |
|---|---|---|---|
| `ruff check backend/app --select F,E9` | 102 errors (6 F821 undefined names, 2 F823, 1 F811, 1 F402, 1 F541, 3 F841, 88 F401) | 95 errors: 88 F401 + 7 F841 only (no undefined/shadowed names). Unused imports are F-36, Phase 5. | 89 (86 F401 + 3 F841; includes `backend/migrations`) |
| Pre-commit gate (`F,E9` minus `F401,F841`) | 13 errors | pass | pass |
| Backend `pytest -m "not live"` | 300 passed, 35 failed, 11 errors, 4 skipped | 343 passed, 24 failed, 1 error, 2 skipped. 23 baseline failures now pass. 2 tests newly fail only in the full run (rate limiter `429` ordering; both pass in isolation, as does `test_sap_restriction::test_rag_endpoint_refusal`). The remaining failures are pre-existing: rate limiter (F-06, Phase 2), forced-off settings, older test drift. | **411 passed, 6 failed, 0 errors, 4 skipped**. No failure is new compared with the baseline or Phase 1. Remaining: 3 tests expecting a `direct_llm` label where the app (and another test) use `conversational`; `test_integration_real_retriever_and_chunk_uuids` (pre-existing tier-name drift); 2 tests needing `WEB_FALLBACK_ENABLED`, which the test environment forces off. |
| Frontend `npm run lint` (oxlint) | exit 1 (rules-of-hooks errors in DocumentManagementPage.tsx) | exit 1, unchanged (F-45, Phase 5) | exit 1, the same 22 errors, all in DocumentManagementPage.tsx (F-45) |
| Frontend `npx tsc --noEmit -p tsconfig.app.json` | pass | pass | pass (also `tsconfig.node.json`) |
| Frontend `npx vitest run` | 10 passed | 10 passed | 14 passed; production build passes and contains the CSP |

Baseline failure causes:
- 10 errors + 1 failure: the F-02 `NameError`.
- About 9: the in-process rate limiter returning `429`/missing `access_token` to the shared test client (F-06, Phase 2).
- 7: tests that need settings I forced off for safety (`WEB_FALLBACK_ENABLED`, vision, style classifier).
- `test_invalid_jwt_token_rejected`: a leaked test dependency override (fixed, see below).
- The rest: older test drift (`conversational` vs `direct_llm` labels, removed `/api/auth/demo`, admin-key fixtures,
  tier names, pgvector column check).

## Log

| Finding | Status | Files changed | Tests added / updated | Notes |
|---|---|---|---|---|
| F-02 | fixed | `backend/app/services/rag_service.py`, `.pre-commit-config.yaml`, `backend/app/corpus/corpus_builder.py`, `backend/app/services/conversation_memory_service.py` | `backend/tests/offline_rag.py` (offline harness), `test_audit_rag_pipeline.py::test_f02_*` | Confirmed red→green: the new test fails with the exact `NameError` on the old code. All 6 F821 were in `rag_service.py`. Also fixed 2 real F823 bugs (`corpus_builder` functions always raised `UnboundLocalError`), F811 and F541. Pre-commit runs `ruff --select F,E9`; F401/F841 ignored until F-36. |
| (test infra) | fixed | `backend/tests/conftest.py` | autouse fixture clears `app.dependency_overrides` after each test | `test_document_upload_extraction` left a fake current user installed, so `test_invalid_jwt_token_rejected` saw 200. The app was correct; the leak hid auth regressions. |
| F-03 | fixed | `rag_service.py`, `backend/app/api/messages.py` | `test_f03_stream_never_emits_text_before_verification`, `test_f03_stream_text_matches_verified_answer_without_repair`, `test_f03_interrupted_stream_does_not_persist_unverified_text` | Draft buffered; verified text streamed after `verifying_claims`. Interrupted streams persist nothing (chose "persist nothing" over a new source_type, so no UI change was needed). |
| F-04 | fixed | `rag_service.py`, `config.py`, `schemas/rag.py`, `frontend/src/types/index.ts`, `frontend/src/services/api.ts`, `GroundingScoreBadge.tsx` | `test_f04_simple_sap_question_goes_through_retrieval_by_default`, `test_f04_small_talk_skips_retrieval_and_is_reported_unverified`; updated `test_query_router.py` (fast-path tests run with the flag on and assert unverified), `test_followup_and_greetings.py` | All 18 `1.0`/`"verified"` literals on paths that skip retrieval replaced. Fast path behind `SIMPLE_SAP_FAST_PATH_ENABLED` (DECISION). |
| F-38 | fixed | `backend/app/api/rag.py`, `backend/app/services/evidence_markers.py` | `backend/tests/test_audit_markers.py` (stripper at chunk sizes 1–64, legacy markers, endpoint test) | Also fixed a latent stripper leak: a marker following a stray `[` (`[[E1]`) was emitted. |
| F-23 | fixed | `backend/app/services/llm_service.py`, `rag_service.py`, `backend/evaluation/run_full_dev_baseline.py` | rewrote `test_adaptive_rag_pipeline.py::test_e_diagnostics_tracking` (fake Groq client; per-call results independent; singleton has no state attributes); `test_answer_style_router.py` streaming test | `GenerationResult` dataclass. `generate_answer(result=…)` / `generate_answer_result()`. |
| F-49 | fixed | `rag_service.py` | `test_f49_*` (2 tests); updated `test_automatic_source_fallback.py` to opt in explicitly and to pin `WEB_FALLBACK_ENABLED` | |
| F-09 | fixed | `llm_service.py`, `config.py`, frontend Markdown renderers | `test_prompt_security_filters.py` (image removal, approved host and spoofed suffix) | Generated Markdown images and links to unapproved hosts are removed; React Markdown blocks images and restricts links to http(s)/mailto. `ALLOWED_LINK_HOSTS` is configurable. |
| F-10 | fixed | `llm_service.py`, `rag_service.py` | `test_prompt_security_filters.py` (evidence delimiter escaping and prompt formatting) | Retrieved evidence, chat summary and recalled/recent history are wrapped as untrusted blocks; system rules prohibit following embedded instructions and disallow URLs/images sourced only there. |
| F-21 | partial | `schemas/rag.py` | `test_prompt_security_filters.py::test_rag_query_has_a_bounded_character_limit` | RAG query capped at 4,000 characters. Attachment, per-user daily budget and chunked body limits remain open. |
| F-45 | fixed | `frontend/src/pages/DocumentManagementPage.tsx` | `npm run lint`, `npx tsc --noEmit -p tsconfig.app.json` | Moved the admin redirect below component hooks; lint no longer reports rules-of-hooks errors. TypeScript strict mode remains unenabled. |
| F-50 | partial | `backend/evaluation/run_full_dev_baseline.py`, `backend/evaluation/*_evaluation_results.json`, `backend/evaluation/golden/*` | `test_prompt_security_filters.py::test_self_generated_gold_cannot_produce_retrieval_metrics`, `test_published_baseline_results_are_marked_invalid` | Legacy self-generated gold is marked invalid and excluded from retrieval metrics; existing result JSON files carry an invalidity warning; added schema and 10-row blank template. Human-authored golden runner and metrics remain to do. |
| F-05 | partial | `config.py`, `services/data_redaction.py`, `llm_service.py`, `query_rewriter.py`, `image_vision_service.py` | `test_llm_egress_controls.py` | Text-provider egress requires explicit `LLM_ALLOWED_PROVIDERS`; free-tier models default off; configured provider/model order is honored; email, IBAN, phone and 10-digit account values are redacted and counts/token estimates are audited. Vision egress is separately off by default because screenshot pixels are not text-redacted. Review all provider adapters and approve egress policy before enabling. |
| F-27 | partial | `rag_service.py`, `backend/app/services/public_payload.py`, `messages.py`, `rag.py` | `test_f27_sync_and_stream_paths_produce_the_same_answer`, `test_f27_parity_holds_when_repair_and_guard_change_the_draft`, `test_public_done_event_is_an_allowlist`, `test_rag_stream_done_hides_diagnostics_and_model_names_from_regular_user`; updated `test_bp_block_regression.py`, `test_sap_restriction.py` | Shared `_answer_pipeline` (rag_service 2,018 → 1,733 lines). Still duplicated: early routing and memory branches. Found during this work: the non-admin SSE `done` event leaked `diagnostics`; it is now built from an allowlist. |
| F-48 | needs-human | `HUMAN_ACTIONS.md` | — | Rotation and history-rewrite commands documented, not run. |
| F-06 | fixed | `backend/app/security/ratelimit.py` (new), `main.py`, `api/auth.py`, `config.py`, `tests/conftest.py` | `test_audit_auth.py::test_f06_*` (random `Authorization` header does not reset the login limit; spoofed `X-Forwarded-For` ignored; per-account lockout including the correct password; success clears failures; unknown emails lock too; memory store cap and expiry) | Redis backend via `limits` implemented but **not verified** (no `limits`/Redis available). Per-process fallback logs a production warning. Test counters reset between tests. |
| F-39 | fixed | `security/auth.py` (`authenticate_user`), `api/auth.py` | `test_f39_*` (exactly one bcrypt check for existing and unknown emails; duplicate registration pays the hashing cost) | Registration status code (201 vs 400) still differs; full hiding needs e-mail verification (HUMAN_ACTIONS). |
| F-29 | fixed (pulled forward from Phase 4) | `backend/alembic.ini`, `backend/migrations/` (env, `0001_baseline`), `database.py`, `config.py` | `test_audit_migrations.py` (test DB at head and idempotent; a truly empty database built from scratch twice; startup refuses an outdated schema with `AUTO_MIGRATE=false`); fixed stale `test_embedding_columns_are_pgvector_384` | Created scratch DB `sap_brim_ai_empty_test` (pgvector only) for the fresh-build test (HUMAN_ACTIONS §7). |
| F-01 | fixed (DECISION defaults) | `config.py`, `models/user.py`, `models/document.py`, `migrations/0002_access_groups.py`, `security/access.py` (new), `retrieval_service.py`, `rag_service.py`, `schemas/auth.py`, `api/auth.py`, `api/admin.py`, `api/documents.py`, `document_processing_service.py`, frontend `LoginPage.tsx`, `AuthContext.tsx`, `api.ts`, `types/index.ts` | `test_audit_access.py` (against the test DB: a user outside the group cannot retrieve the chunk, directly or via `process_query`; group members and admins can; registration off by default; invite code; admin group endpoints) | Licensed-content decision remains with the owner (HUMAN_ACTIONS §3). Also applies `document_filter` before ranking on the dense channel (part of F-14). |
| F-40 | fixed | `security/auth.py` (`create_access_token`, `decode_access_token`), `api/auth.py`, `main.py`, `config.py` | `test_f40_*` (no email claim; iss/aud/jti present; wrong aud/iss/missing jti rejected; 401 from the API; `alg: none` rejected; startup rejects non-HMAC algorithms) | Existing tokens are invalid after deploy (users sign in once). |
| F-25 | fixed | `models/audit_event.py`, `migrations/0003_audit_events.py`, `services/audit_log.py` (new), `security/auth.py`, `api/auth.py`, `api/admin.py`, `api/documents.py`, `api/messages.py` | `test_audit_events.py` (login success/failure/logout, admin login and non-admin attempt, document delete with admin key, admin key use, share create/revoke, endpoint admin-only and filterable, write failure never breaks a request) | |
| F-37 | fixed | `security/stream_tokens.py` (new), `schemas/message.py`, `api/messages.py`, frontend `api.ts`, `ChatPage.tsx` | `test_audit_partial.py` (token bound to user/chat/expiry; missing/forged/foreign rejected; accepted once; interrupted answer not shareable; stream starts with a valid token); frontend test for the `stream` event; updated `test_edit_prompt.py` event order | Breaking `save-partial` body change (CHANGELOG). |
| F-33 | partial | frontend `api.ts` (`authFetch`, `setUnauthorizedHandler`), `AuthContext.tsx`, `LoginPage.tsx`, `AdminLoginPage.tsx` | 3 vitest cases (401 with token calls the handler once; without token it does not; stream 401 reports too) | Global 401 handling and cross-tab logout done; **refresh tokens not added** (DECISION, HUMAN_ACTIONS §5–6). |
| F-26 | partial (DECISION) | `main.py`, frontend `vite.config.ts`, `index.html`, `public/theme-init.js` | `test_f26_*` (no-store and lock-down CSP on API and stream responses); production build checked to contain the CSP meta and no inline script | Cookie/BFF migration documented, not done (HUMAN_ACTIONS §6). |
| F-42 | fixed | `main.py`, `api/admin.py` | `test_f42_*` (health is status-only; system-health admin-only; docs routes 404 with `ENVIRONMENT=production`, checked in a subprocess) | |
| F-41 | fixed | `main.py` (with the F-06 `ProxyHeadersMiddleware`) | `test_f41_*` (https from a trusted proxy accepted; forwarded proto from untrusted peer ignored; plain-HTTP `/health` probe allowed) | |
| (test drift) | fixed | `test_admin_portal_security.py`, `test_document_management_dashboard.py`, `test_document_attachment_flow.py` | — | Tests still used the removed `/api/auth/demo` or sent no admin credentials; they now act as a real user or administrator. |
