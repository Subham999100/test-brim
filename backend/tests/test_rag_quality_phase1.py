"""Phase 1 of the RAG quality work (docs/superpowers/specs/2026-11-04-rag-quality-phase0-1-design.md):
keep strong-model answers (last-resort models, Groq truncation) and keep prompts lean (Scholar history, repair
evidence). Offline: providers are fakes."""

from types import SimpleNamespace

import pytest

from backend.app.config import settings
from backend.app.services.llm_service import LLMService

LAST_RESORT = "allam-2-7b,liquid/lfm-2.5-2.6b:free"


def _service(monkeypatch, groq=("strong-a", "allam-2-7b"), gemini=("gem-a",), openrouter=("or-a", "liquid/lfm-2.5-2.6b:free")):
    monkeypatch.setattr(settings, "LLM_ALLOWED_PROVIDERS", "groq,gemini,openrouter")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "LLM_LAST_RESORT_MODELS", LAST_RESORT, raising=False)
    service = LLMService()
    service.groq_api_key = service.gemini_api_key = service.openrouter_api_key = "test-key"
    service.GROQ_MODELS, service.GEMINI_MODELS, service.OPENROUTER_MODELS = list(groq), list(gemini), list(openrouter)
    monkeypatch.setattr(service, "_prepare_external_prompts", lambda _p, _m, prompt, system: (prompt, system))
    return service


def _recording_providers(service, answers):
    """Fake provider calls that record which models each provider was offered; `answers` maps model -> reply."""
    offered = []

    def fake(provider):
        def call(prompt, system_prompt, result=None, regeneration_index=None):
            models = service._get_models(provider)
            offered.append((provider, models))
            for model in models:
                if model in answers:
                    if result is not None:
                        result.model, result.provider = model, provider
                    return answers[model]
            return None
        return call

    service._call_groq, service._call_gemini, service._call_openrouter = fake("groq"), fake("gemini"), fake("openrouter")
    return offered


# ---------------------------------------------------------------- last-resort models

def test_the_normal_pass_does_not_offer_last_resort_models(monkeypatch):
    service = _service(monkeypatch)
    assert service._get_models("groq") == ["strong-a"]
    assert service._get_models("openrouter") == ["or-a"]


def test_last_resort_models_answer_only_after_every_provider_failed(monkeypatch):
    service = _service(monkeypatch)
    offered = _recording_providers(service, {"allam-2-7b": "small-model answer"})

    assert service.generate_answer("question", []) == "small-model answer"
    assert offered == [
        ("groq", ["strong-a"]), ("gemini", ["gem-a"]), ("openrouter", ["or-a"]),
        ("groq", ["allam-2-7b"]),
    ], "Groq -> Gemini -> OpenRouter first; tiny models only as a last resort, in the same provider order"


def test_a_strong_answer_never_reaches_the_last_resort(monkeypatch):
    service = _service(monkeypatch)
    offered = _recording_providers(service, {"gem-a": "gemini answer", "allam-2-7b": "small-model answer"})

    assert service.generate_answer("question", []) == "gemini answer"
    assert offered == [("groq", ["strong-a"]), ("gemini", ["gem-a"])]


def test_repair_and_sprint_completions_use_the_same_cascade(monkeypatch):
    service = _service(monkeypatch)
    offered = _recording_providers(service, {"liquid/lfm-2.5-2.6b:free": "last resort"})

    assert service.generate_completion("prompt") == "last resort"
    assert [provider for provider, _ in offered] == ["groq", "gemini", "openrouter", "groq", "openrouter"]


def test_streaming_reaches_last_resort_models_only_when_no_provider_streamed(monkeypatch):
    service = _service(monkeypatch)
    offered = []

    def streamer(provider):
        def stream(prompt, system_prompt, regeneration_index=None):
            models = service._get_models(provider)
            offered.append((provider, models))
            if "allam-2-7b" in models:
                yield "small "
                yield "stream"
        return stream

    service._stream_groq, service._stream_gemini, service._stream_openrouter = (
        streamer("groq"), streamer("gemini"), streamer("openrouter")
    )
    assert "".join(service._stream_configured("prompt", "system")) == "small stream"
    assert offered[:3] == [("groq", ["strong-a"]), ("gemini", ["gem-a"]), ("openrouter", ["or-a"])]
    assert offered[3] == ("groq", ["allam-2-7b"])
    assert service._get_models("groq") == ["strong-a"], "the pool is restored after streaming"


def test_without_last_resort_setting_every_model_stays_in_the_normal_pass(monkeypatch):
    service = _service(monkeypatch)
    monkeypatch.setattr(settings, "LLM_LAST_RESORT_MODELS", "")
    assert service._get_models("groq") == ["strong-a", "allam-2-7b"]


# ---------------------------------------------------------------- Groq truncation

PARAGRAPH = "Convergent Invoicing bills the billable items of a contract account. " * 8


class FakeGroqClient:
    """Replies come from `replies`: each is (content, finish_reason) or an Exception to raise."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.requests.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        content, finish_reason = reply
        choice = SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish_reason)
        return SimpleNamespace(choices=[choice], usage=None)


def _groq(monkeypatch, replies, models=("strong-a", "strong-b")):
    import importlib

    # Limits learned from 413 errors are process-wide; start each test without them.
    learned = getattr(importlib.import_module("backend.app.services.llm_service"), "_GROQ_OBSERVED_TPM", None)
    if learned is not None:
        learned.clear()
    service = _service(monkeypatch, groq=models)
    client = FakeGroqClient(replies)
    monkeypatch.setattr("groq.Groq", lambda **_kwargs: client)
    return service, client


def test_a_truncated_groq_answer_is_continued_instead_of_discarded(monkeypatch):
    service, client = _groq(monkeypatch, [(PARAGRAPH + "\n\nThe invoicing run then", "length"),
                                          ("posts the invoices to FI-CA.", "stop")])
    meta = SimpleNamespace()
    from backend.app.services.llm_service import GenerationResult
    meta = GenerationResult()

    answer = service._call_groq("prompt", "system", result=meta)

    assert answer.startswith(PARAGRAPH.strip()[:40])
    assert answer.endswith("posts the invoices to FI-CA.")
    assert meta.model == "strong-a" and meta.was_continued is True and meta.is_truncated is False
    assert [request["model"] for request in client.requests] == ["strong-a", "strong-a"]


def test_when_continuation_fails_the_complete_paragraphs_are_kept(monkeypatch):
    service, client = _groq(monkeypatch, [(PARAGRAPH + "\n\n" + PARAGRAPH + "\n\nThe invoicing run then", "length"),
                                          RuntimeError("429 rate limit")])
    from backend.app.services.llm_service import GenerationResult
    meta = GenerationResult()

    answer = service._call_groq("prompt", "system", result=meta)

    assert answer and answer.endswith(PARAGRAPH.strip())
    assert "The invoicing run then" not in answer, "the cut-off sentence is dropped"
    assert meta.model == "strong-a" and meta.is_truncated is True


def test_a_tiny_truncated_answer_still_moves_to_the_next_model(monkeypatch):
    service, client = _groq(monkeypatch, [("Short start", "length"), RuntimeError("429 rate limit"),
                                          ("Full answer from model b.", "stop")])
    from backend.app.services.llm_service import GenerationResult
    meta = GenerationResult()

    assert service._call_groq("prompt", "system", result=meta) == "Full answer from model b."
    assert meta.model == "strong-b"


# ---------------------------------------------------------------- lean prompts

@pytest.fixture
def plain_guidance(monkeypatch):
    # Keeps the answer-style router offline (no LLM classifier call).
    monkeypatch.setattr(settings, "ANSWER_STYLE_ROUTER_ENABLED", False)


def _history(count=20, size=5000):
    return [
        {"role": "user" if index % 2 == 0 else "assistant",
         "content": f"MSG{index:02d} " + ("billing detail [E3] " * (size // 20))}
        for index in range(count)
    ]


def test_scholar_history_keeps_six_messages_verbatim_and_excerpts_the_rest(monkeypatch, plain_guidance):
    service = _service(monkeypatch)
    prompt = service._build_answer_prompt("How is it configured?", [], "knowledge_base", chat_history=_history())

    for index in range(20):
        assert f"MSG{index:02d}" in prompt, "every message in the window is still represented"
    assert "[E3]" not in prompt, "old evidence markers are not fed back"
    assert len(prompt) < 30000, "20 x 5,000-character messages no longer go in whole"
    latest = prompt[prompt.index("MSG19"):]
    assert latest.count("billing detail") >= 50, "the latest messages keep substantial text"


def test_short_history_is_unchanged_apart_from_markers(monkeypatch, plain_guidance):
    service = _service(monkeypatch)
    history = [{"role": "user", "content": "What is a provider contract?"},
               {"role": "assistant", "content": "It is the customer contract in FI-CA [E1]."}]
    prompt = service._build_answer_prompt("How is it created?", [], "knowledge_base", chat_history=history)
    assert "What is a provider contract?" in prompt
    assert "It is the customer contract in FI-CA." in prompt


def test_the_question_is_restated_right_before_the_task(monkeypatch, plain_guidance):
    service = _service(monkeypatch)
    prompt = service._build_answer_prompt("How is it configured?", [], "knowledge_base", chat_history=_history(4, 200))
    restated = prompt.index("QUESTION TO ANSWER NOW:\nHow is it configured?")
    assert prompt.index("RECENT CONVERSATION CONTEXT") < restated < prompt.index("TASK:")


def test_repair_prompt_uses_the_same_bounded_evidence_as_the_draft(monkeypatch, plain_guidance):
    service = _service(monkeypatch)
    captured = {}
    monkeypatch.setattr(service, "generate_completion",
                        lambda prompt, system_prompt=None, regeneration_index=None: captured.setdefault("prompt", prompt) and "")
    evidence = [{"chunk_text": f"PASSAGE{index:02d} " + "x" * 1180, "document_name": f"Doc {index}"} for index in range(12)]

    service.repair_answer("q", "candidate answer", ["claim"], [], evidence)

    assert "PASSAGE00" in captured["prompt"]
    assert "PASSAGE11" not in captured["prompt"], "evidence is cut to the draft's character budget"


# ---------------------------------------------------------------- Groq token budget

TOO_LARGE = ("Error code: 413 - {'error': {'message': 'Request too large for model `strong-a` in organization `org` "
             "service tier `on_demand` on tokens per minute (TPM): Limit 8000, Requested 9214, please reduce your "
             "message size and try again.', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}")


def test_groq_learns_the_real_per_minute_limit_and_retries_the_same_model(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_TOKENS_PER_MINUTE", 9000)
    service, client = _groq(monkeypatch, [RuntimeError(TOO_LARGE), ("Answer from strong-a.", "stop")])
    prompt = "p" * 18000  # about 4,000 tokens
    from backend.app.services.llm_service import GenerationResult
    meta = GenerationResult()

    assert service._call_groq(prompt, "system", result=meta) == "Answer from strong-a."
    assert [request["model"] for request in client.requests] == ["strong-a", "strong-a"]
    first, retry = (request["max_tokens"] for request in client.requests)
    assert retry < first and retry <= 8000 - 4000 - 150 + 50, "the retry fits the real 8,000-token limit"
    assert service._groq_max_tokens("x", model="strong-a") <= 8000, "the learned limit is remembered"
