# RAG generation failure diagnosis

## 2026-11-02: "I couldn't generate a verified response right now" in Scholar

### Observed root cause

The user asked "What are the types in SAP BRIM?" in Scholar. The two failing requests were traced through `audit_events` (`llm_egress` rows record provider, model and token estimate; no prompt text) and through `messages.source_type` (no message content was read).

What happened in each request:
- The answer-style classifier ran.
- Groq `qwen/qwen3.8-27b` generated the draft.
- The repair call to the same model failed within 0.1 s, because Groq's per-minute token budget was already spent by the draft.
- `openai/gpt-oss-120b` produced the repair.
- The request ended `unavailable` about 2 s later, with no further LLM call.

So the LLM tiers worked. The answer was discarded by the pipeline:

1. `grounding_service.verify_answer` rejected the answer. The gate fails if any standard SAP identifier in the answer is missing from the selected passages, or if more than 25% of sentences have low term overlap. Broad questions ("types", "components") trip this easily.
2. `_answer_pipeline` retries with web evidence only when web search has not already run. The local `.env` enables the multi-source comparator, so Tavily had already run and the retry was skipped.
3. The rejected answer was then replaced by `UNAVAILABLE_RESPONSE` (audit F-03 fail-closed rule).

Contributing configuration (live probe, one-word prompt per model; see `KNOWN_ISSUES.md` LLM-002):
- `LLM_MODEL=llama-3.3-70b-versatile` 404s for this Groq key;
- `gemini-3.8-flash` is over quota;
- `apodex/apodex-1.1-mini:free` was retired by OpenRouter.

All other configured models answered, and every provider key was present. The frontend renders the backend text as-is; it was not substituting its own error.

### Fix: fallback architecture

```text
Question -> retrieval -> LLM tier 1 (Groq) -> tier 2 (Gemini) -> tier 3 (OpenRouter)
   generated -> claim verification -> repair -> guard -> (web retry if web not yet used)
       passes                 -> published as verified/partial
       still fails            -> unconfirmed identifiers/contradictions removed, published with a notice (never "verified")
   no tier generated -> approved SAP web results (reused or new Tavily search) -> linked answer, "unverified"
       no web results        -> ALL_METHODS_UNAVAILABLE_RESPONSE, verification_status "unavailable"
```

* LLM tiers (`llm_service.generate_answer`): each tier is its own `_call_groq` / `_call_gemini` / `_call_openrouter` with a model cascade, a 45 s timeout and no SDK retries. The log names the tier that answered and each tier that failed, by category (`auth_error`, `rate_limited`, `timeout`, `invalid_response`, `provider_error`). `ModelCooldowns` skips a model after a 404 (1 h), a 429 (retry-after, else 30 s) or a timeout (60 s). A rejected API key (401, "invalid api key", "API key not valid", PermissionDenied) now skips the whole provider for 1 h, so a configuration error is not retried for every model on every request. A bare 403 does not count: OpenRouter uses it for a single prompt flagged by moderation.
* Web search fallback (`rag_service._final_web_search`, `_web_fallback_result`): reuses web passages this request already fetched (legacy web fallback, comparator candidates, selected passages); otherwise one Tavily search restricted to approved SAP domains. The answer lists up to 5 sources, each a clickable title link with the sentences that share the most terms with the question. No knowledge-base text is included. Links pass through `filter_generated_links` with `ALLOWED_LINK_HOSTS` plus the approved SAP search domains. Respects `WEB_FALLBACK_ENABLED`.
* Grounding rejection (`rag_service._publish_unverified`): `apply_guard` removes sentences with critical failures, contradictions, or unconfirmed identifiers (status `unconfirmed_identifier`, whose user note does not repeat the identifier), then re-verifies. Status is `partial`/`unverified`, never `verified`. `UNVERIFIED_ANSWER_NOTE` is appended, with up to 3 approved web links when web evidence was used. `repair_info["published_unverified"]` and the admin `selection_summary` record it.
* Messages: `UNAVAILABLE_RESPONSE` is unchanged and still used by Sprint and memory recall when no tier answers. Scholar's final error is `ALL_METHODS_UNAVAILABLE_RESPONSE`.

### Verification

`backend/tests/test_llm_web_fallback_chain.py`, offline with stubbed providers and Tavily, covers:
- each tier used only after the previous ones fail, with the unchanged prompt and the tier log line;
- 401 skipping a provider's remaining models;
- web fallback with links (sync and stream);
- web search empty, raising or disabled, giving the all-methods error;
- grounding rejection publishing a labelled answer (sync and stream);
- unconfirmed identifier removal, and web-linked unverified answers;
- with the real verifier: a simple SAP BRIM question coming back `verified`, and the complex components question keeping its section structure.

Results and the wider regression run are recorded in `CHANGELOG_ENGINEERING.md` (2026-11-02).

## 2026-10-29 (superseded in part)

`LLMService.generate_answer()` used to return ranked evidence excerpts as if they were a generated answer when the providers failed. That shim was removed: generation never returns retrieved text. That still holds. The web-search fallback above shows public SAP web pages as clearly labelled, linked sources, never as a model answer. Provider defaults: Groq, Gemini and OpenRouter are allowlisted in tier order; an explicitly empty `LLM_ALLOWED_PROVIDERS` disables cloud generation; `LLM_ALLOW_FREE_TIER=false` drops `:free` models. Regular-user JSON and SSE omit provider/model and failure diagnostics.
