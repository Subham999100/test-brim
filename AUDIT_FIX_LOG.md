# Audit fix log

Branch `audit-fixes` (from `security-remediation-20261028` @ `0f44c57`). Findings: `AUDIT_REPORT.md` F-01 – F-59.
Owner actions and product decisions: `HUMAN_ACTIONS.md`. API/config changes: `CHANGELOG_AUDIT.md`.

## Summary

Status after **Phase 1** (Phase 2–6 not started yet).

| Status | Count |
|---|---|
| fixed | 6 (F-02, F-03, F-04, F-23, F-38, F-49) |
| partial | 1 (F-27) |
| skipped | 0 |
| needs-human | 1 (F-48: rotation and history rewrite listed in HUMAN_ACTIONS.md) |
| not started | 51 |

### Verification before and after

Environment for backend tests: PostgreSQL 16 + pgvector in Docker, database `sap_brim_ai_test` only
(the `conftest.py` guard refuses any database not ending in `_test`). LLM, search and vision keys blanked
and `WEB_FALLBACK_ENABLED=false`, so no external calls; `-m "not live"`.

| Check | Baseline (before any change) | After Phase 1 |
|---|---|---|
| `ruff check backend/app --select F,E9` | 102 errors (6 F821 undefined names, 2 F823, 1 F811, 1 F402, 1 F541, 3 F841, 88 F401) | 95 errors: 88 F401 + 7 F841 only (no undefined/shadowed names). Unused imports are F-36, Phase 5. |
| Pre-commit gate (`F,E9` minus `F401,F841`) | 13 errors | pass |
| Backend `pytest -m "not live"` | 300 passed, 35 failed, 11 errors, 4 skipped | 343 passed, 24 failed, 1 error, 2 skipped. 23 baseline failures now pass. 2 tests newly fail only in the full run (rate limiter `429` ordering; both pass in isolation, as does `test_sap_restriction::test_rag_endpoint_refusal`). The remaining failures are pre-existing: rate limiter (F-06, Phase 2), forced-off settings, older test drift. |
| Frontend `npm run lint` (oxlint) | exit 1 (rules-of-hooks errors in DocumentManagementPage.tsx) | exit 1, unchanged (F-45, Phase 5) |
| Frontend `npx tsc --noEmit -p tsconfig.app.json` | pass | pass |
| Frontend `npx vitest run` | 10 passed | 10 passed |

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
| F-27 | partial | `rag_service.py`, `backend/app/services/public_payload.py`, `messages.py`, `rag.py` | `test_f27_sync_and_stream_paths_produce_the_same_answer`, `test_f27_parity_holds_when_repair_and_guard_change_the_draft`, `test_public_done_event_is_an_allowlist`, `test_rag_stream_done_hides_diagnostics_and_model_names_from_regular_user`; updated `test_bp_block_regression.py`, `test_sap_restriction.py` | Shared `_answer_pipeline` (rag_service 2,018 → 1,733 lines). Still duplicated: early routing and memory branches. Found during this work: the non-admin SSE `done` event leaked `diagnostics`; it is now built from an allowlist. |
| F-48 | needs-human | `HUMAN_ACTIONS.md` | — | Rotation and history-rewrite commands documented, not run. |
