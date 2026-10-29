# Audit remediation changelog (API and configuration)

Branch `audit-fixes`. Finding IDs refer to `AUDIT_REPORT.md`. Lists every change to public API shapes,
behaviour clients can observe, and configuration.

## New environment variables

| Variable | Default | Purpose | Finding |
|---|---|---|---|
| `ALLOWED_LINK_HOSTS` | `help.sap.com,learning.sap.com,community.sap.com,support.sap.com` | Hosts the backend permits in generated Markdown links after post-filtering. Exact host and subdomain matching are used. | F-09 |
| `LLM_ALLOWED_PROVIDERS` | empty | Comma-separated external text providers allowed to receive prompts (`groq`, `gemini`, `openrouter`). Empty disables cloud text generation and uses the local grounded fallback. | F-05 |
| `LLM_PROVIDER` | `local` | Preferred provider. It is used first only when included in `LLM_ALLOWED_PROVIDERS`; `local` disables cloud calls. | F-05 |
| `LLM_MODEL` | empty | Optional preferred model, moved to the front of the selected provider's configured model list. | F-05 |
| `LLM_ALLOW_FREE_TIER` | `false` | Permit model IDs with `:free` for text and vision only after explicit operator opt-in. | F-05 |
| `LLM_GROQ_MODELS` | `qwen/qwen3.8-27b,openai/gpt-oss-120b,openai/gpt-oss-20b,allam-2-7b` | Candidate Groq text model order; `LLM_MODEL` is moved first when Groq is selected. | F-05 |
| `LLM_GEMINI_MODELS` | `gemini-2.5-flash,gemini-3.8-flash` | Candidate Gemini text model order; `LLM_MODEL` is moved first when Gemini is selected. | F-05 |
| `LLM_OPENROUTER_MODELS` | `liquid/lfm-2.5-2.6b:free,nvidia/nemotron-3.5-lightning:free,apodex/apodex-1.1-mini:free` | Candidate OpenRouter model order; free models are filtered unless opted in, and `LLM_MODEL` is moved first when OpenRouter is selected. | F-05 |
| `VISION_EXTERNAL_ENABLED` | `false` | Explicitly permit screenshot/image payloads to be sent to approved cloud vision providers. Images are not pixel-redacted. | F-05 |
| `MAX_UPLOAD_BYTES` | `52428800` (50 MiB) | Per-file cap for admin document uploads. | F-20 |
| `MAX_TOTAL_UPLOAD_BYTES` | `104857600` (100 MiB) | Aggregate document bytes accepted from one upload request; ASGI body cap includes 1 MiB multipart overhead. | F-20 |
| `ALLOW_EXTENDED_UPLOAD_TYPES` | `false` | Opt in to `.json`, `.xml`, `.sql`, `.yaml`, and `.yml` document uploads. | F-20 |
| `MAX_PDF_PAGES` | `500` | Reject PDF extraction when the document exceeds this page count. | F-20 |
| `MAX_REQUEST_BODY_BYTES` | `12582912` (12 MiB) | Counted body cap for non-document-upload requests, including chunked requests. | F-20 |
| `SIMPLE_SAP_FAST_PATH_ENABLED` | `false` | Opt-in: answer simple SAP definitions from model memory without retrieval (always reported unverified). | F-04 |
| `RATE_LIMIT_ENABLED` | `true` | Master switch for rate limits and login lockout. | F-06 |
| `REDIS_URL` | empty | Shared rate-limit storage (needs `limits[redis]`); empty means per-process memory. | F-06 |
| `TRUSTED_PROXIES` | empty | Comma-separated reverse-proxy IPs whose `X-Forwarded-For`/`-Proto` are believed. | F-06, F-41 |
| `RATE_LIMIT_MAX_KEYS` | `50000` | Cap on in-memory rate-limit keys. | F-06 |
| `AUTH_RATE_LIMIT_PER_MINUTE` | `20` | Requests per minute to `/api/auth/*` per client. | F-06 |
| `LOGIN_RATE_LIMIT_PER_MINUTE` | `10` | Login attempts per minute per client IP. | F-06 |
| `LOGIN_MAX_FAILURES` / `LOGIN_LOCKOUT_WINDOW_SECONDS` | `5` / `900` | Account lockout after N failed passwords within the window. | F-06 |
| `ANSWER_RATE_LIMIT_PER_MINUTE` / `EXTRACT_RATE_LIMIT_PER_MINUTE` | `12` / `10` | Previously hard-coded limits, now one budget per user across all chats. | F-06 |
| `AUTO_MIGRATE` | `true` | Apply Alembic migrations at startup; set `false` in production and migrate as a deploy step. | F-29 |
| `REGISTRATION_ENABLED` | `false` | Public self-registration. **Default changed: registration is now off.** | F-01 |
| `INVITE_CODE` | empty | When set (at least 12 characters), registration requires it. | F-01 |
| `DEFAULT_ACCESS_GROUP` | `all` | Group given to new users and documents. | F-01 |
| `JWT_ALGORITHM` | `HS256` | Now read from the environment; must be HS256/HS384/HS512 or startup fails. | F-40 |
| `JWT_ISSUER` / `JWT_AUDIENCE` | `sap-brim-assistant` / `sap-brim-assistant-api` | Claims added to and verified on every token. | F-40 |

## Changed behaviour of existing settings

| Setting | Before | After | Finding |
|---|---|---|---|
| `AUTO_MULTI_SOURCE_FALLBACK` | Weak document match triggered the GitHub + web comparator and forced repository search even when `REPO_SOURCE_ENABLED`/`MULTI_SOURCE_COMPARE_ENABLED` were false. | Triggers only when one of those flags is true; repository search follows `REPO_SOURCE_ENABLED`. | F-49 |

## API and payload changes

| Endpoint / payload | Change | Compatible? | Finding |
|---|---|---|---|
| `RAGQueryRequest.query` | Maximum length is 4,000 characters; larger inputs receive the standard Pydantic `422` response. | Yes for valid requests | F-21 |
| `POST /api/documents/upload` | Uploads are spooled incrementally; body requests over `MAX_TOTAL_UPLOAD_BYTES` plus multipart allowance receive `413`. Unsupported/mismatched formats and per-file cap violations appear in the existing per-file `errors` list. | Compatible response shape | F-20 |
| `PATCH /api/documents/{id}/tier` | Administrators can classify a document into an allowlisted authority tier; changes are audited and invalidate retrieval cache. New/unclassified documents default to `self_authored` (lowest authority). Document admin list/detail responses include `source_tier`. | Additive admin API and fields | F-53 |
| `GET /api/auth/me/export`, `DELETE /api/auth/me` | Authenticated account export includes owned chats and attached data without credentials or embeddings. Deletion cascades chats/messages/attachments/shares; the final administrator cannot self-delete. | Additive endpoints; delete returns 204 | F-31 |
| `INCLUDE_SELF_AUTHORED_DOCS` | `false` | Exclude documents classified `self_authored` from retrieval before candidate ranking. Set true only when project-authored references should be used as evidence. | F-08/F-54 |
| `ATTACHMENT_RETENTION_DAYS` | `365` | Retention cutoff uses the parent message's creation time; `0` disables cleanup. `py -3.14 backend/scripts/purge_expired_attachments.py` reports a dry-run count; pass `--apply` to delete expired attachment rows. | F-31 |
| Generated answer Markdown | Images are removed. Links to hosts outside `ALLOWED_LINK_HOSTS` are reduced to their label. Frontend Markdown also blocks image rendering and applies `target="_blank"` with `noopener noreferrer nofollow` to http(s)/mailto links. | Rendering behavior | F-09 |
| `POST /api/chats/{id}/messages?stream=true`, `POST …/messages/stream`, `POST …/{message_id}/edit`, `POST /api/rag/query/stream` | `token` events now arrive only after the `verifying_claims` status and carry the verified answer (in word chunks), not the live LLM draft. The event types and order (`status`… `token`… `done`) are unchanged. | Yes; time to first token is later. | F-03 |
| Same streaming endpoints | A stream that ends before `done` no longer stores the partial text as an `interrupted` assistant message. | Yes | F-03 |
| `RAGQueryResponse.grounding_score` (`POST /api/rag/query`, admin response) | Type changed from `float` to `float \| null`. `null` when the answer did not go through retrieval (small talk, conversation-memory answers, opt-in fast path). | Clients must accept `null`. | F-04 |
| All answer payloads | Paths that skip retrieval now return `grounding_score: null` and `verification_status: "unverified"` instead of `1.0` / `"verified"`. Simple SAP questions now go through retrieval, so they return citations and real grounding scores (admins). | Values changed | F-04 |
| SSE `done` event for regular users (both stream endpoints) | Built from an allowlist: `type, answer, message_id, follow_up_questions, images, citations ([]), web_sources ([]), source_type (null), grounding_score (null), external_search_used (false)`. Internal fields (`diagnostics`, `validation_audit`, `answer_decision`, scores, `model_used`, `provider_used`, …) are no longer present at all (previously some were present as `null`, and `diagnostics` leaked). | Yes for the frontend; clients reading removed keys get `undefined`. | F-27 |
| `GET/POST /api/chats/{id}/messages` (sync), regular users | `verification_status` is `null` instead of a hard-coded `"verified"`. | Yes | F-27 |
| `process_query` result / stream `done` (admins) | Both paths now return the same keys: `images` from the sync path (visual search when explicitly asked), and `model_used`, `provider_used`, `failed_over`, `regeneration_count`, `shadow_audit`, `grounded_score` from the stream path. `diagnostics.model_used`/`provider_used` come from the request's own generation and can be `null` (no provider succeeded or local fallback). | Additive | F-23, F-27 |
| Answer text for regular users | Legacy `[KB_n]`/`[WEB_n]`/`[REPO_n]` markers are stripped everywhere (they were stripped on `/api/rag` only). | Yes | F-38 |
| `POST /api/auth/login`, `/admin-login` | New `429` ("Too many login attempts") on per-IP limit or account lockout, even with a correct password while locked. | Clients must handle 429 | F-06 |
| `POST /api/auth/register` | `403` when `REGISTRATION_ENABLED=false` (the new default) or the invite code is wrong. New optional body field `invite_code`. | **Breaking by default** (registration off) | F-01 |
| `UserResponse` (login, register, `/auth/me`) | New field `groups: string[]`. | Additive | F-01 |
| Access tokens | No `email` claim; new `iss`, `aud`, `jti`, all verified. Tokens issued before this change are rejected (users sign in again once). | **Breaking for existing tokens** | F-40 |
| `GET /api/admin/users`, `PATCH /api/admin/users/{id}/groups` | New, admin JWT only. | Additive | F-01 |
| `PATCH /api/documents/{id}/access` (`{"allowed_groups": [...]}`) | New, admin or admin key. Document list/detail responses include `allowed_groups`. | Additive | F-01 |
| Retrieval for regular users | Only chunks of documents sharing one of the user's groups are used (everything starts in `all`, so nothing changes until an admin restricts a document). | Behaviour | F-01 |
| `GET /api/admin/audit-events` | New, admin JWT only (not the admin key); filters `action`, `actor_id`, `outcome`, `since`; `limit` ≤ 200, `offset`. | Additive | F-25 |
| Answer streams (all SSE answer endpoints in `/api/chats/...`) | First event is now `{"type": "stream", "stream_id": "..."}`, before `user_message`. Unknown event types were already ignored by the client. | Additive | F-37 |
| `POST /api/chats/{id}/messages/save-partial` | Body now `{content, stream_id}`; `stream_id` required (`422` without), must be the server-issued id for this user and chat (`403`), accepted once (`409`). | **Breaking** (frontend updated) | F-37 |
| `POST /api/chats/{id}/messages/{mid}/share` | `409` for interrupted (stopped) assistant answers. | Behaviour | F-37 |
| All API responses (except docs routes) | `Cache-Control: no-store`, `Pragma: no-cache`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'`. | Yes | F-26 |
| Frontend production build | Strict CSP `<meta>`; inline theme script moved to `/theme-init.js`. | Yes | F-26 |
| `GET /health` | Returns only `{"status", "database": {"status"}}`; counts, model, version moved to new admin-only `GET /api/admin/system-health`. Reachable over plain HTTP in production. | **Fields removed** | F-42, F-41 |
| `/docs`, `/redoc`, `/openapi.json` | Not served when `ENVIRONMENT=production`. | Production only | F-42 |
| `POST /api/admin/documents/ingest` | Unchanged API; the dependency now returns the principal (`"admin_key"` or the admin user) for auditing. | Yes | F-25 |

## Internal Python API (for maintainers)

- `LLMService` no longer has `last_model_used`, `last_provider_used`, `failed_over`, `last_finish_reason`,
  `is_truncated`, `was_continued`, `last_estimated_tokens`, `last_configured_max_tokens`. Use
  `generate_answer(..., result=GenerationResult())` or `generate_answer_result(...)` (F-23).
- `RAGService` gained `_answer_pipeline`, `_drain`, `_build_citations`, `_generation_diagnostics`,
  `_verified_token_events`. The streaming answer path calls `llm_service.generate_answer`, not `stream_answer` (F-03, F-23, F-27).
- `evidence_markers.LEGACY_MARKER_PATTERN` added. `StreamingMarkerStripper` handles legacy markers and `[[E1]` (F-38).
- `backend.app.services.public_payload.public_done_event` added (F-27).
- Schema migrations: Alembic in `backend/alembic.ini` / `backend/migrations`; revisions `0001_baseline`,
  `0002_access_groups`, `0003_audit_events`. Migrations must stay idempotent (`IF NOT EXISTS`). `init_db` no longer
  runs ad-hoc `ALTER TABLE`s (F-29).
- New modules: `security/ratelimit.py`, `security/access.py`, `security/stream_tokens.py`, `services/audit_log.py`,
  `models/audit_event.py`. `security.auth.authenticate_user`, `decode_access_token` (all decoding goes through it).
- `retrieval_service.hybrid_search(..., allowed_groups=None)` and `retrieve(..., allowed_groups=None)`:
  `None` means unrestricted (F-01).
