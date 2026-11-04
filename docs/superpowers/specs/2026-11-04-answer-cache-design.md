# Answer cache for repeated standalone questions — design

Date: 2026-11-04 · Status: awaiting owner review · Related: token savings B (per-answer storage and totals)

## Goal

When a question that was already answered is asked again as a standalone question, return the stored answer
instantly instead of running retrieval and the LLM again. The user sees "Instant answer · saved ~N tokens".
This is the largest real saving available: one person's question pays for everyone's repeats.

Non-goals: semantic ("similar question") matching, caching follow-up questions, caching answers built from a
user's own chats or files, the non-streaming `POST /messages` path (the chat UI only streams).

## Owner decisions (2026-11-04)

| Topic | Decision |
| --- | --- |
| Who can receive a cached answer | Every user whose **document access groups are identical** to the original asker's. Admins (unrestricted access) have their own cache space and never share with users. |
| Matching | Exact match after normalisation only (case, whitespace and trailing `?`/`!`/`.` ignored). No similarity matching, so no false matches. |

## Defaults chosen (flag in review if wrong)

| Topic | Default | Why |
| --- | --- | --- |
| Modes | Sprint and Scholar, cached separately (mode is part of the key). | Different answer styles. |
| Lifetime | 7 days (`ANSWER_CACHE_TTL_HOURS=168`). | Web-backed Scholar answers age. |
| Kill switch | `ANSWER_CACHE_ENABLED=true`. | Operator can turn it off without a deploy. |
| Knowledge-base change | Any upload, delete, reprocess or access-group change clears the whole cache. | All of them already call `retrieval_service.invalidate_cache()`; the answer cache is cleared there too. Simple and never stale. |
| Thumbs-down | A dislike on a cached or cache-sourced answer deletes that cache entry. | A bad answer must not spread. |
| Regenerate | Always bypasses the cache and never overwrites an entry with a regeneration. | Regenerate means "give me a different answer". |

## Eligibility

A **request** may be served from or stored to the cache only if all hold:

1. It is the first user message of the chat (no earlier messages, no rolling summary).
2. It has no attachments.
3. It is not a regeneration or an edit.
4. Sprint: the memory step recalled nothing and produced no memory answer (`recalled` empty, `answer` None).
   Scholar: no historical memory was recalled.

An **answer** is stored only if it completed (`done` event) and its `source_type` is one of `knowledge_base`,
`web`, `sprint`, `conversational` and its `verification_status` is not `unavailable`, `rejected` or an error.
Refusals, memory answers, errors, interrupted and unavailable answers are never stored.

## Key and privacy

`cache_key = sha256(version | mode | access_groups | normalised_question)` where `access_groups` is the sorted,
comma-joined result of `retrieval_groups(user)` or `*admin*` for unrestricted users. Only the hash is stored,
never the question text. The answer, citations, web sources and images are stored, as they already are in
`messages`. Every hit is rendered through the same admin/public filters as a fresh answer
(`visible_content`, `public_done_event`), so regular users never receive internal fields.

## Data model (Alembic `0009_answer_cache`, additive, idempotent; after B's `0008`)

`answer_cache`: `id`, `cache_key` (char 64, unique), `mode` (varchar 10), `answer` (text), `source_type`,
`grounding_score` (float, null), `verification_status` (varchar 30, null), `payload` (JSON: citations,
web_sources, images, follow_up_questions), `tokens_used` and `tokens_baseline` (int: the original answer's cost),
`llm_provider`, `llm_model` (admin-only display), `source_message_id` (FK messages, ON DELETE SET NULL),
`hits` (int, default 0), `created_at`, `last_hit_at` (null), `expires_at` (index).

`messages` (new nullable column): `answer_cache_key` (char 64) on answers stored to or served from the cache,
so a thumbs-down can evict the right entry; `served_from_cache` (bool, default false) for the "Instant answer"
label after reload.

## Flow (both streaming handlers)

1. Eligible request → look up a live entry (`expires_at > now`).
2. **Hit:** emit the usual SSE sequence (`stream`, `user_message`, status "Found a verified answer to this exact
   question", the answer as tokens, `done` with `cached: true` and
   `token_usage = {used: 0, baseline: entry.tokens_baseline, saved: entry.tokens_baseline}`); persist the
   assistant message with `served_from_cache=true`, the cache key, its citation/web rows and the token figures
   from B; increment `hits`. No retrieval, no LLM call.
3. **Miss:** generate as today; after `done`, if the answer is eligible, upsert the entry (a concurrent
   duplicate insert loses quietly on the unique key).
4. Lookup or store failures are logged and ignored: the cache can never break answering.

## Admin

`DELETE /api/admin/answer-cache` (super admin) clears it. Admin answer badges show "cache hit" and the original
provider/model. Expired rows are ignored by lookups and deleted when a new entry is stored (no background
job exists in this codebase, and none is added).

## UI

An "Instant answer" chip in the answer header (live and after reload) and the existing savings popup with the
cached saving. B's chat line and Settings total include cache savings automatically (they sum stored figures).

## Testing

Key normalisation and group/mode separation; eligibility (second message, attachments, regeneration, recall,
refusal and unavailable answers excluded); hit path makes no retrieval or LLM call (fakes assert not called);
regular users get only public fields on a hit; admin and user caches separate; TTL expiry; clear on
`invalidate_cache`; eviction on thumbs-down; regenerate bypass; failure isolation (DB error on lookup still
answers); migration idempotence; frontend chip and popup.

## Risks

Stale content inside the TTL when a web source changes (mitigated by TTL, KB clear, thumbs-down, kill switch).
Org and individual users with identical groups share entries (owner decision). Saved figures are estimates,
like the rest of the token meter.
