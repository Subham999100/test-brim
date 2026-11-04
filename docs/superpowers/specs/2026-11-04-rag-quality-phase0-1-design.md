# RAG answer quality — phases 0 and 1 (design and plan)

Date: 2026-11-04 · Owner decision: build phase 0 (honest evaluation + live baseline) and phase 1 (stop discarding
strong-model answers, token hygiene) now; phases 2-4 after the measured result. Self-authored documents: listed for
owner review, not changed.

## Evidence behind the plan (read-only investigation, 2026-11-04)

* The 2026-10-26 baseline numbers are not measurements: the LLM judge never ran (`answer_quality_evaluator.py:221`
  requires "groq" in the model id), key facts reduce to the token "address" (lower-case-only regex), claim rates
  are constants, gold chunks are the system's own top-3 (circular) and results are cached by id.
* 93% of answers were written by fallback models, 64% by `allam-2-7b`. Mechanism (verified in code and live):
  the configured `llama-3.3-70b-versatile` 404s; `qwen3-27b` / `gpt-oss-120b` answer, but with
  `GROQ_TOKENS_PER_MINUTE=9000` a 5-8k-token Scholar prompt leaves ~1-2k output tokens, reasoning models hit
  `finish_reason=length`, and `llm_service.py:1027-1032` discards the answer and moves to the next, smaller model.
  The cascade is ordered by provider, so `allam-2-7b` runs before `gemini-2.5-flash`.
* Scholar sends the last 20 messages verbatim with no per-message cap (`llm_service.py:801-806`), including old
  `[E#]` markers; repair resends draft + uncapped evidence + all instructions through the top of the chain.
* Live probe today: Groq qwen3-27b, gpt-oss-120b, gpt-oss-20b, allam-2-7b OK; llama-3.3-70b 404; gemini-2.5-flash
  OK, gemini-3.8-flash timeout; OpenRouter lfm-2.6b 429, nemotron OK; Tavily key empty (web tier unavailable).

## Phase 0 — honest evaluation

New, separate harness (the old one stays, marked unreliable): `backend/evaluation/quality_eval.py`,
`quality_judge.py`, dataset `datasets/quality_eval_v1.jsonl`.

* **Dataset (hand-written, reviewed):** 24 single-turn questions — conceptual, functional, technical,
  configuration, troubleshooting, integration (3-4 each), 2 hallucination traps, 1 false premise, 1 out-of-scope —
  plus 5 multi-turn conversations (12 turns) covering the follow-up defects found ("How is it created?",
  "Ok, which transactions are used?", "Give me some examples", "and in CI?", "Can you explain it with an
  example?"). Key points are conservative, well-established SAP BRIM facts; risky specifics are avoided.
* **Runs the real Scholar pipeline** (`rag_service.process_query`) against the real knowledge base with a regular
  user's access groups; multi-turn history is carried in memory exactly as the API passes it. The evidence the
  model actually received is captured by wrapping `llm_service.generate_answer` inside the evaluation process only.
* **Metrics:**
  * Retrieval relevance — judge marks each passage given to the model relevant/irrelevant (precision of the
    context actually used, not circular gold).
  * Correctness — judge score 1-5 plus key-point coverage (judge per point, not regex).
  * Hallucination rate — answers with a judge-flagged fabricated claim or an identifier that is neither in the
    evidence nor in the identifier registry; traps pass only without fabrication.
  * Conversation continuity — judge: does the follow-up answer address the follow-up in the earlier topic?
  * Operations — answering model, weak-model rate, unavailable rate, latency p50/p95, tokens used.
* **Judge:** `gemini-2.5-flash`, temperature 0, JSON output, different provider from the generator.
* **Safety:** results written under a label (`results/quality_<label>.*`), never overwriting another label;
  pause between questions (default 20 s) to stay inside free-tier limits. Uses the real `.env` keys; prints no
  secrets. Writes only the usual `llm_egress` audit rows to the database.

## Phase 1 — keep strong answers, lean prompts (items 8, 9)

1. **Last-resort models:** `LLM_LAST_RESORT_MODELS` (default `allam-2-7b,liquid/lfm-2.5-2.6b:free`) are skipped in
   the normal Groq → Gemini → OpenRouter pass and tried only after every other model failed, before web search.
   Provider priority is unchanged.
2. **No discarded answers:** a Groq answer cut at the token limit is continued (as Gemini/OpenRouter already are)
   instead of thrown away; reasoning effort is kept low where the model supports it.
3. **History hygiene (Scholar):** latest 6 messages verbatim (each capped), older in-window messages as the same
   500-character excerpts Sprint uses; `[E#]` markers and verification notes stripped from history.
4. **Repair size:** repair uses the same bounded evidence context as the draft, not the uncapped list.
5. Re-run the evaluation with label `phase1` and compare with `baseline`.

## Tests

Offline unit tests for every pure part (dataset schema, judge prompt/JSON parsing, identifier support,
aggregation, model ordering, Groq continuation, history capping) written before the code; existing LLM, chat-mode,
token and regeneration suites re-run after each change.
