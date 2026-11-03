# Engineering decisions

## 2026-11-02 — Scholar publishes grounding-rejected answers with a notice; web search is the last fallback

Context: Scholar answered "What are the types in SAP BRIM?" with "I couldn't generate a verified response right now." The audit trail showed every provider tier had responded. The claim verifier rejected the generated answer, and the pipeline (audit F-03, "unverified drafts are never shown") replaced it with the generic message. Web search was not retried because it had already run. The owner asked for a meaningful answer instead of a generic error, without ever claiming an answer is verified when it is not, and for web search as the final fallback after the three LLM tiers.

Decision: an answer that still fails the grounding gate after repair (and after the web retry, which now also adopts an equally ranked web-backed candidate) is published with `verification_status` `partial`/`unverified`, never `verified`. Before publication:
- sentences with contradicted or critical claims, or with SAP identifiers the verifier classed as unconfirmed (`critical_unsupported_claims`), are removed by `apply_guard`;
- a visible note is appended, plus up to three approved SAP web links when web evidence was used.

When no LLM tier answers, approved SAP web results (already fetched in the request, else a new Tavily search when `WEB_FALLBACK_ENABLED`) become a structured, linked answer marked unverified. Only when that also fails does the user see `ALL_METHODS_UNAVAILABLE_RESPONSE`.

Alternatives: keep failing closed (the reported bug); lower `ANSWER_GROUNDING_THRESHOLD` or relax the identifier rule (silently publishes weaker answers as "verified"); fall back to an ungrounded Sprint-style answer (discards retrieved evidence).

Reasoning: the gate stays unchanged and still decides `verified`. What changed is that a rejected answer is labelled rather than discarded, and the unsafe parts are still removed.

Consequences: F-03's "never shown" guarantee no longer holds for Scholar. The guarantees are now: unverified text is never streamed before verification finishes, and it is never labelled verified. Regular users see the in-text note. `verification_status` is still exposed to them only when it is `unavailable`. Web links appear in the answer text for web-fallback and web-backed unverified answers; knowledge-base citations stay admin-only. Landing and How-it-works copy updated. Relevant files: `services/rag_service.py` (`_publish_unverified`, `_final_web_search`, `_web_fallback_result`), `services/llm_service.py`, `tests/test_llm_web_fallback_chain.py`.

## 2026-10-27 — Comparisons require grounded RAG

Context: the router's simple-definition patterns treated “difference between” SAP component questions as direct LLM answers.

Decision: route comparisons through `COMPLEX_SAP` retrieval/grounding.

Alternatives: retain direct response for speed; special-case a small set of static comparisons.

Reasoning: relationships between BRIM components are more than an acronym definition and can require product/process evidence. The change is narrow and preserves direct routing for true definitions.

Consequences: comparison questions may take longer and depend on available evidence; they gain the normal RAG safeguards. Relevant files: `services/query_router.py`, `tests/test_query_router.py`.

## 2026-10-27 — Streaming RAG uses the same supplied-chat ownership contract

Context: synchronous `/rag/query` returned 404 for an inaccessible chat ID, while the streaming endpoint did not.

Decision: reject inaccessible supplied IDs before opening the streaming flow.

Consequence: callers now receive a consistent 404 instead of an unscoped generation. Relevant file: `api/rag.py`.

## 2026-10-27 — Summarize only rows outside the recent 20, with a per-chat watermark

Context: the former updater appended only the latest exchange and could not identify older rows that had left the immediate context window.

Decision: select out-of-window rows in `(created_at, id)` order, serialize updates with a chat-row lock, and commit bounded sanitized excerpts together with a timestamp/id watermark.

Alternatives: keep appending only the current exchange; regenerate a summary from all history on every turn; introduce a separate summary table or external summarizer.

Reasoning: this fits the current Chat summary field and PostgreSQL transaction model, makes retries idempotent, and avoids extra provider calls. Full message rows and semantic retrieval remain the detailed history source.

Consequences: the 4,000-character extractive summary is lossy. It cannot guarantee preservation of every fact; messages remain separately stored. Relevant files: `conversation_memory_service.py`, `models/chat.py`, `database.py`.
