"""LLM judge for the phase-0 answer-quality evaluation (see quality_eval.py).

The judge runs on a different provider from the answer generator (Gemini vs the Groq-first chain), at
temperature 0, and must return one JSON object. Anything malformed is rejected rather than guessed, so a turn
the judge could not score is reported as such instead of being counted as good or bad.
"""

import json
import re
import time
from typing import Any, Dict, List, Optional

# The model receives up to 1,200 characters per document passage and 1,800 per web passage.
PASSAGE_CHARS = 1800
MAX_PASSAGES = 8

_EXPECTATIONS = {
    "answer": "The assistant should answer the question correctly and specifically.",
    "no_fabrication": "This is a trap: the named identifier does not exist. The assistant must not invent a purpose, "
                      "fields or usage for it; saying it cannot confirm or find it is the correct behaviour.",
    "correct_premise": "The question contains a false premise. The assistant should correct the premise rather than "
                       "answer as if it were true.",
    "refuse": "The question is outside SAP. The assistant should politely decline.",
}


def _passages(evidence: List[Dict[str, Any]]) -> str:
    blocks = []
    for index, passage in enumerate((evidence or [])[:MAX_PASSAGES], 1):
        title = passage.get("document_name") or passage.get("title") or passage.get("url") or "source"
        text = " ".join(str(passage.get("chunk_text") or passage.get("snippet") or "").split())[:PASSAGE_CHARS]
        blocks.append(f"[P{index}] {title}\n{text}")
    return "\n\n".join(blocks) if blocks else "(no passages were given to the assistant)"


def build_judge_prompt(
    *,
    query: str,
    expect: str,
    key_points: List[str],
    answer: str,
    evidence: List[Dict[str, Any]],
    history: Optional[List[Dict[str, Any]]] = None,
    follow_up_topic: Optional[str] = None,
) -> str:
    """The grading prompt for one turn."""
    conversation = "\n".join(
        f"{'User' if item.get('role') == 'user' else 'Assistant'}: {' '.join(str(item.get('content') or '').split())[:600]}"
        for item in (history or [])
    ) or "(none: this is the first question)"
    points = "\n".join(f"{index}. {point}" for index, point in enumerate(key_points, 1))
    n_passages = min(len(evidence or []), MAX_PASSAGES)
    follow_up = (
        f"This is a follow-up question. It refers to: {follow_up_topic}. Set \"continuity\" to true only if the "
        "answer addresses the follow-up within that topic."
        if follow_up_topic else "This is not a follow-up question. Set \"continuity\" to null."
    )
    return f"""You are a strict SAP BRIM expert grading an AI assistant's answer. Grade only what is written.

EARLIER CONVERSATION:
{conversation}

QUESTION:
{query}

EXPECTED BEHAVIOUR:
{_EXPECTATIONS.get(expect, _EXPECTATIONS['answer'])}
{follow_up}

KEY POINTS A GOOD ANSWER COVERS:
{points}

PASSAGES THE ASSISTANT WAS GIVEN ({n_passages}):
{_passages(evidence)}

ASSISTANT ANSWER:
{answer.strip() or '(empty)'}

Return ONLY one JSON object with exactly these fields:
- "correctness": integer 1-5 (5 = fully correct, specific and complete; 3 = partly correct or generic;
  1 = wrong, empty or off-topic). For traps, premises and refusals, grade the expected behaviour.
- "key_points": array of {len(key_points)} booleans, one per key point, true if the answer covers it.
- "fabricated_claims": array of short strings: specific SAP claims in the answer (transaction codes, tables,
  fields, configuration paths, Fiori apps, process facts) that you believe are false or invented. List a claim
  only if it is wrong or made up, not merely because the passages do not mention it, and never for wording,
  formatting or citation placement. Empty array if none.
- "addresses_question": boolean, true if the answer responds to what was actually asked.
- "continuity": boolean or null (see above).
- "verbatim_copy": boolean, true if most of the answer is copied passage text rather than an explanation.
- "passage_relevance": array of {n_passages} booleans, one per passage P1..P{n_passages}, true if the passage
  is relevant to answering the question.
"""


def _bools(value: Any, size: int) -> List[bool]:
    items = [bool(item) for item in value] if isinstance(value, list) else []
    return (items + [False] * size)[:size]


def parse_judge_output(raw: Optional[str], *, n_key_points: int, n_passages: int) -> Optional[Dict[str, Any]]:
    """The judge's verdict sized to this turn, or None when the output is unusable."""
    match = re.search(r"\{.*\}", raw or "", re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    correctness = data.get("correctness")
    if not isinstance(correctness, int) or isinstance(correctness, bool) or not 1 <= correctness <= 5:
        return None
    if not isinstance(data.get("key_points"), list):
        return None
    claims = data.get("fabricated_claims")
    continuity = data.get("continuity")
    return {
        "correctness": correctness,
        "key_points": _bools(data.get("key_points"), n_key_points),
        "fabricated_claims": [str(claim) for claim in claims] if isinstance(claims, list) else [],
        "addresses_question": bool(data.get("addresses_question")),
        "continuity": None if continuity is None else bool(continuity),
        "verbatim_copy": bool(data.get("verbatim_copy")),
        "passage_relevance": _bools(data.get("passage_relevance"), min(n_passages, MAX_PASSAGES)),
    }


def retry_after_seconds(message: str, default: float = 20.0) -> float:
    """How long a provider asked us to wait ("try again in 7.5s" / "in 1m2.5s"), else `default`."""
    match = re.search(r"try again in (?:(\d+)m)?(\d+(?:\.\d+)?)s", message or "")
    if not match:
        return default
    return int(match.group(1) or 0) * 60 + float(match.group(2))


class GroqJudge:
    """Judge on Groq (default gpt-oss-120b, temperature 0, JSON mode). Run it after generation, never during,
    so it does not compete with the answering models for the per-minute token budget."""

    def __init__(self, api_key: str, model: str = "openai/gpt-oss-120b", max_attempts: int = 4):
        from groq import Groq

        self._client = Groq(api_key=api_key, timeout=120.0, max_retries=0)
        self.model_name = model
        self._max_attempts = max_attempts

    def __call__(self, prompt: str) -> Optional[str]:
        for attempt in range(self._max_attempts):
            try:
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                    **({"reasoning_effort": "low"} if self.model_name.startswith("openai/gpt-oss") else {}),
                )
                return response.choices[0].message.content if response.choices else None
            except Exception as exc:  # noqa: BLE001 - reported as an unscored turn
                message = str(exc)
                if attempt + 1 < self._max_attempts and any(code in message for code in ("429", "413", "503", "timeout")):
                    time.sleep(retry_after_seconds(message) + 1)
                    continue
                return None
        return None


class GeminiJudge:
    """Calls Gemini (temperature 0, JSON). One retry after a pause on rate limits or timeouts."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: float = 90.0):
        import google.generativeai as genai  # the SDK the application already uses

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)
        self.model_name = model
        self._timeout = timeout

    def __call__(self, prompt: str) -> Optional[str]:
        for attempt in range(2):
            try:
                response = self._model.generate_content(
                    prompt,
                    generation_config={"temperature": 0, "response_mime_type": "application/json"},
                    request_options={"timeout": self._timeout},
                )
                return response.text
            except Exception as exc:  # noqa: BLE001 - reported as an unscored turn
                message = str(exc).lower()
                if attempt == 0 and any(term in message for term in ("429", "quota", "deadline", "timeout", "503")):
                    time.sleep(30)
                    continue
                return None
        return None
