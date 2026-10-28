# Audit remediation changelog (API and configuration)

Branch `audit-fixes`. Finding IDs refer to `AUDIT_REPORT.md`. Lists every change to public API shapes,
behaviour clients can observe, and configuration.

## New environment variables

| Variable | Default | Purpose | Finding |
|---|---|---|---|
| `SIMPLE_SAP_FAST_PATH_ENABLED` | `false` | Opt-in: answer simple SAP definitions from model memory without retrieval (always reported unverified). | F-04 |

## Changed behaviour of existing settings

| Setting | Before | After | Finding |
|---|---|---|---|
| `AUTO_MULTI_SOURCE_FALLBACK` | Weak document match triggered the GitHub + web comparator and forced repository search even when `REPO_SOURCE_ENABLED`/`MULTI_SOURCE_COMPARE_ENABLED` were false. | Triggers only when one of those flags is true; repository search follows `REPO_SOURCE_ENABLED`. | F-49 |

## API and payload changes

| Endpoint / payload | Change | Compatible? | Finding |
|---|---|---|---|
| `POST /api/chats/{id}/messages?stream=true`, `POST …/messages/stream`, `POST …/{message_id}/edit`, `POST /api/rag/query/stream` | `token` events now arrive only after the `verifying_claims` status and carry the verified answer (in word chunks), not the live LLM draft. The event types and order (`status`… `token`… `done`) are unchanged. | Yes; time to first token is later. | F-03 |
| Same streaming endpoints | A stream that ends before `done` no longer stores the partial text as an `interrupted` assistant message. | Yes | F-03 |
| `RAGQueryResponse.grounding_score` (`POST /api/rag/query`, admin response) | Type changed from `float` to `float \| null`. `null` when the answer did not go through retrieval (small talk, conversation-memory answers, opt-in fast path). | Clients must accept `null`. | F-04 |
| All answer payloads | Paths that skip retrieval now return `grounding_score: null` and `verification_status: "unverified"` instead of `1.0` / `"verified"`. Simple SAP questions now go through retrieval, so they return citations and real grounding scores (admins). | Values changed | F-04 |
| SSE `done` event for regular users (both stream endpoints) | Built from an allowlist: `type, answer, message_id, follow_up_questions, images, citations ([]), web_sources ([]), source_type (null), grounding_score (null), external_search_used (false)`. Internal fields (`diagnostics`, `validation_audit`, `answer_decision`, scores, `model_used`, `provider_used`, …) are no longer present at all (previously some were present as `null`, and `diagnostics` leaked). | Yes for the frontend; clients reading removed keys get `undefined`. | F-27 |
| `GET/POST /api/chats/{id}/messages` (sync), regular users | `verification_status` is `null` instead of a hard-coded `"verified"`. | Yes | F-27 |
| `process_query` result / stream `done` (admins) | Both paths now return the same keys: `images` from the sync path (visual search when explicitly asked), and `model_used`, `provider_used`, `failed_over`, `regeneration_count`, `shadow_audit`, `grounded_score` from the stream path. `diagnostics.model_used`/`provider_used` come from the request's own generation and can be `null` (no provider succeeded or local fallback). | Additive | F-23, F-27 |
| Answer text for regular users | Legacy `[KB_n]`/`[WEB_n]`/`[REPO_n]` markers are stripped everywhere (they were stripped on `/api/rag` only). | Yes | F-38 |

## Internal Python API (for maintainers)

- `LLMService` no longer has `last_model_used`, `last_provider_used`, `failed_over`, `last_finish_reason`,
  `is_truncated`, `was_continued`, `last_estimated_tokens`, `last_configured_max_tokens`. Use
  `generate_answer(..., result=GenerationResult())` or `generate_answer_result(...)` (F-23).
- `RAGService` gained `_answer_pipeline`, `_drain`, `_build_citations`, `_generation_diagnostics`,
  `_verified_token_events`. The streaming answer path calls `llm_service.generate_answer`, not `stream_answer` (F-03, F-23, F-27).
- `evidence_markers.LEGACY_MARKER_PATTERN` added. `StreamingMarkerStripper` handles legacy markers and `[[E1]` (F-38).
- `backend.app.services.public_payload.public_done_event` added (F-27).
