"""
Per-question token accounting for the "tokens saved" counter in the chat UI.

Counts are estimates (about four characters per token), never provider bills. What Clyptus actually
sends and receives and the generic-chatbot baseline use the same estimator, so the comparison is like
for like. The baseline is what a typical chatbot would process for the same question in one call: the
same instructions, the whole conversation resent unsummarised, every retrieved passage, the question
and the answer. Clyptus instead sends the top reranked passages and a rolling summary, and answers some
questions (conversation memory, refusals) without any LLM call.

The meter is only active while `metered()` steps the answer stream; LLM calls made outside a metered
stream are not recorded.
"""

import contextvars
import functools
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Iterator, Optional, TypeVar

CHARS_PER_TOKEN = 4

T = TypeVar("T")


def estimate_tokens(chars: int) -> int:
    """Token estimate for a character count, rounded up."""
    return -(-max(chars, 0) // CHARS_PER_TOKEN)


@dataclass
class TokenMeter:
    llm_chars: int = 0  # prompts and replies of the LLM calls that answered, for this question
    system_chars: int = 0  # largest system prompt that was answered; the baseline chatbot gets the same instructions
    retrieved_chars: int = 0  # every retrieved passage, before reranking narrowed them down
    # The latest prompt sent, counted only once a reply arrives: a failed attempt (rate limit, bad key,
    # timeout) is replaced by the retry's prompt and never counted.
    staged_chars: int = 0
    staged_system_chars: int = 0

    def commit_staged(self) -> None:
        self.llm_chars += self.staged_chars
        self.system_chars = max(self.system_chars, self.staged_system_chars)
        self.staged_chars = self.staged_system_chars = 0

    @property
    def used_tokens(self) -> int:
        return estimate_tokens(self.llm_chars)

    def summary(self, *, question: str, answer: str, conversation_chars: int) -> Dict[str, int]:
        baseline = estimate_tokens(
            self.system_chars + conversation_chars + len(question or "") + self.retrieved_chars + len(answer or "")
        )
        used = self.used_tokens
        return {"used": used, "baseline": baseline, "saved": max(0, baseline - used)}


_active: contextvars.ContextVar[Optional[TokenMeter]] = contextvars.ContextVar("token_meter", default=None)


def metered(events: Iterable[T], meter: TokenMeter) -> Iterator[T]:
    """Steps `events` with `meter` active. The meter is set around each step rather than once, because
    Starlette may run every step of a streaming response in a different worker thread and context."""
    iterator = iter(events)
    while True:
        token = _active.set(meter)
        try:
            item = next(iterator)
        except StopIteration:
            return
        finally:
            _active.reset(token)
        yield item


def stage_prompt(prompt: Optional[str], system_prompt: Optional[str] = None) -> None:
    """A prompt about to be sent; replaces an earlier staged prompt that got no reply."""
    meter = _active.get()
    if meter is None:
        return
    meter.staged_chars = len(prompt or "") + len(system_prompt or "")
    meter.staged_system_chars = len(system_prompt or "")


def commit_staged() -> None:
    """Counts the staged prompt now, for a follow-up request (continuation) that stages its own prompt."""
    meter = _active.get()
    if meter is not None:
        meter.commit_staged()


def record_reply(text: Any) -> None:
    """A non-empty reply proves the staged prompt was processed, so both are counted."""
    meter = _active.get()
    if meter is not None and isinstance(text, str) and text:
        meter.commit_staged()
        meter.llm_chars += len(text)


def record_retrieved(passages: Optional[Iterable[Dict[str, Any]]]) -> None:
    meter = _active.get()
    if meter is None:
        return
    for passage in passages or []:
        text = passage.get("chunk_text") or passage.get("content") or passage.get("text") or ""
        meter.retrieved_chars += len(text) if isinstance(text, str) else 0


def meter_reply(func: Callable) -> Callable:
    """Records what a provider call returns: the string of a plain call, or every streamed chunk."""
    if inspect.isgeneratorfunction(func):
        @functools.wraps(func)
        def stream_wrapper(*args, **kwargs):
            for chunk in func(*args, **kwargs):
                record_reply(chunk)
                yield chunk
        return stream_wrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        reply = func(*args, **kwargs)
        record_reply(reply)
        return reply
    return wrapper
