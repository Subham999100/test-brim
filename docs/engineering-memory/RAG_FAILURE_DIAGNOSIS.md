# RAG generation failure diagnosis

## Confirmed code path

`LLMService.generate_answer()` previously called `_generate_grounded_local_response()` after the configured cloud providers failed. That helper extracted and ranked sentences from retrieved evidence, then returned the excerpts as if they were a generated answer. The RAG verifier could accept copied sentences because they matched the evidence. The normal frontend, persistence, and share flows carried that final answer through; they did not create the excerpts.

Provider selection is gated by `LLM_ALLOWED_PROVIDERS`, and a `local` provider preference yields no cloud provider order. With no provider available, generation now returns a stable unavailable message and request-scoped status. The shared RAG pipeline bypasses claim verification for that case and fails closed when verification rejects an answer. Conversation-history generation uses the same safe fallback and marks it unavailable. Sync JSON and SSE preserve the string response contract and report `verification_status: "unavailable"`; regular-user payloads omit provider and failure diagnostics.

## Failure diagnosis and limits

Generation diagnostics distinguish `local_provider_selected`, `provider_policy_denied`, `missing_api_key`, `no_models_allowed`, `rate_limited`, `timeout`, `invalid_response`, and generic `provider_error`. Provider/model calls are not made by the regression harness. There is no provider circuit breaker in this implementation, so `circuit_breaker_open` is not an observed runtime cause. The existing provider adapters use bounded 45-second requests, but there is no whole-request deadline.

The code defaults and `.env.example` can establish intended policy only. Runtime provider keys, allowlists, quotas, and actual provider failures were not inspected because `.env` files and credentials are out of scope. Accordingly, configuration mismatch is a confirmed code-level cause candidate; missing/invalid credentials and quota exhaustion remain runtime hypotheses.

## Verification

`backend/tests/test_rag_generation_unavailable.py` covers local/no-provider behavior, total provider failure, successful provider generation, failure classification, verifier bypass, sync/stream fail-closed behavior, and the public SSE allowlist. The focused selection including `test_audit_rag_pipeline.py` passed 17 tests using offline retrieval, fake providers, and a fake database URL ending in `_test`. `.env` discovery was disabled before importing the application. No live database or provider was used.
