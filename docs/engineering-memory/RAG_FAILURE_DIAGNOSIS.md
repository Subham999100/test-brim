# RAG generation failure diagnosis

## Confirmed code path

`LLMService.generate_answer()` previously called `_generate_grounded_local_response()` after the configured cloud providers failed. That helper extracted and ranked sentences from retrieved evidence, then returned the excerpts as if they were a generated answer. The RAG verifier could accept copied sentences because they matched the evidence. The normal frontend, persistence, and share flows carried that final answer through; they did not create the excerpts.

Provider selection is gated by `LLM_ALLOWED_PROVIDERS`. The defaults now enable Groq, Gemini, and OpenRouter in tier order; configured OpenRouter free-tier models are enabled by default, and `LLM_ALLOW_FREE_TIER=false` skips them. A `local` preference uses the approved order, while an explicitly empty provider allowlist disables external calls. With no provider available, generation returns a stable unavailable message and request-scoped status. The shared RAG pipeline bypasses claim verification for that case and fails closed when verification rejects an answer. Conversation-history generation uses the same safe fallback and marks it unavailable. Sync JSON and SSE preserve the string response contract and report `verification_status: "unavailable"`; regular-user payloads omit provider and failure diagnostics.

## Failure diagnosis and limits

Generation diagnostics distinguish `provider_policy_denied`, `missing_api_key`, `no_models_allowed`, `rate_limited`, `timeout`, `invalid_response`, and generic `provider_error`. The defaults now allow Groq, Gemini, and OpenRouter in tier order; an explicitly empty allowlist remains an opt-out. Provider/model calls are not made by the regression harness. There is no provider circuit breaker in this implementation, so `circuit_breaker_open` is not an observed runtime cause. The existing provider adapters use bounded 45-second requests, but there is no whole-request deadline.

Web search now triggers when document match is below `DOCUMENT_MATCH_THRESHOLD`, even if internal confidence alone would not trigger and the source comparator is disabled. If the grounding gate still rejects a candidate despite strong retrieval scores, the shared pipeline makes one web-backed regeneration attempt before returning unavailable. Empty Siftdog/SearXNG responses now continue to Tavily rather than returning early.

The code defaults and `.env.example` can establish intended policy only. Runtime provider keys, allowlists, quotas, and actual provider failures were not inspected because `.env` files and credentials are out of scope. Accordingly, configuration mismatch is a confirmed code-level cause candidate; missing/invalid credentials and quota exhaustion remain runtime hypotheses.

## Verification

`backend/tests/test_rag_generation_unavailable.py`, `backend/tests/test_provider_search_fallbacks.py`, provider egress tests, search tests, and RAG audit regressions passed 46 tests using offline retrieval and fake providers/search responses. The harness set `_env_file=None` before app settings construction and used a fake database URL ending in `_test`. No live database or provider was used.
