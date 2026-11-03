"""
Scholar fallback chain: LLM tier 1 -> tier 2 -> tier 3 -> approved SAP web search -> clear error.
Also the observed failure: an answer the grounding gate rejected used to become the generic
"couldn't generate a verified response" message although every provider had answered.
"""

import importlib
import logging
from unittest.mock import MagicMock, patch

import pytest

from backend.app.config import settings
from backend.app.services.llm_service import GenerationResult, LLMService, ModelCooldowns, UNAVAILABLE_RESPONSE
from backend.app.services.rag_service import (
    ALL_METHODS_UNAVAILABLE_RESPONSE,
    UNVERIFIED_ANSWER_NOTE,
    WEB_FALLBACK_INTRO,
    rag_service,
)
from backend.tests.offline_rag import offline_rag

# backend.app.services re-exports the llm_service instance under the module's name.
llm_module = importlib.import_module("backend.app.services.llm_service")

SIMPLE_QUESTION = "What are the types in SAP BRIM?"
COMPLEX_QUESTION = "What are the different components of SAP BRIM, and explain their functions?"

BRIM_ROWS = [
    {
        "chunk_id": "chunk-brim-1", "document_id": "doc-brim", "document_name": "SAP BRIM Overview.pdf",
        "source_type": "knowledge_base", "page_number": 3, "section": "Components",
        "chunk_text": (
            "SAP BRIM consists of four main components: Subscription Order Management, Convergent Charging, "
            "Convergent Invoicing and Contract Accounts Receivable and Payable."
        ),
        "snippet": "SAP BRIM consists of four main components.", "vector_score": 0.84, "bm25_score": 4.0, "score": 0.88,
    },
    {
        "chunk_id": "chunk-brim-2", "document_id": "doc-brim", "document_name": "SAP BRIM Overview.pdf",
        "source_type": "knowledge_base", "page_number": 4, "section": "Components",
        "chunk_text": (
            "Subscription Order Management captures subscription orders and manages provider contracts. "
            "Convergent Charging rates usage events in real time using charge plans."
        ),
        "snippet": "Subscription Order Management captures subscription orders.", "vector_score": 0.82,
        "bm25_score": 3.8, "score": 0.86,
    },
    {
        "chunk_id": "chunk-brim-3", "document_id": "doc-brim", "document_name": "SAP BRIM Overview.pdf",
        "source_type": "knowledge_base", "page_number": 5, "section": "Components",
        "chunk_text": (
            "Convergent Invoicing aggregates billable items into consolidated invoices. Contract Accounts "
            "Receivable and Payable posts invoicing documents and manages payments, dunning and collections."
        ),
        "snippet": "Convergent Invoicing aggregates billable items.", "vector_score": 0.8, "bm25_score": 3.6, "score": 0.85,
    },
]

SIMPLE_ANSWER = (
    "SAP BRIM consists of four main components: Subscription Order Management, Convergent Charging, "
    "Convergent Invoicing and Contract Accounts Receivable and Payable. "
    "Subscription Order Management captures subscription orders and manages provider contracts. "
    "Convergent Charging rates usage events in real time using charge plans. "
    "Convergent Invoicing aggregates billable items into consolidated invoices. "
    "Contract Accounts Receivable and Payable posts invoicing documents and manages payments, dunning and collections."
)

COMPLEX_ANSWER = (
    "SAP BRIM consists of four main components: Subscription Order Management, Convergent Charging, "
    "Convergent Invoicing and Contract Accounts Receivable and Payable.\n\n"
    "## Subscription Order Management\n"
    "Subscription Order Management captures subscription orders and manages provider contracts.\n\n"
    "## Convergent Charging\n"
    "Convergent Charging rates usage events in real time using charge plans.\n\n"
    "## Convergent Invoicing\n"
    "Convergent Invoicing aggregates billable items into consolidated invoices.\n\n"
    "## Contract Accounts Receivable and Payable\n"
    "Contract Accounts Receivable and Payable posts invoicing documents and manages payments, dunning and collections."
)

WEB_PASSAGE = {
    "source_type": "web",
    "source_id": "web_1_help.sap.com",
    "title": "SAP Billing and Revenue Innovation Management",
    "url": "https://help.sap.com/docs/SAP_BRIM/overview",
    "domain": "help.sap.com",
    "snippet": "SAP BRIM covers subscription order management, charging, invoicing and contract accounting.",
    "chunk_text": (
        "SAP Billing and Revenue Innovation Management\n"
        "SAP BRIM covers subscription order management, charging, invoicing and contract accounting. "
        "Convergent Charging rates usage in real time. Unrelated navigation text."
    ),
    "score": 0.9,
}


# ---------------------------------------------------------------- LLM tiers 1 -> 2 -> 3

def _three_tier_service() -> LLMService:
    with patch.object(settings, "LLM_PROVIDER", "groq"), \
            patch.object(settings, "LLM_ALLOWED_PROVIDERS", "groq,gemini,openrouter"):
        service = LLMService()
    service.groq_api_key, service.gemini_api_key, service.openrouter_api_key = "test-groq", "test-gemini", "test-or"
    service.GROQ_MODELS, service.GEMINI_MODELS, service.OPENROUTER_MODELS = ["groq-m"], ["gemini-m"], ["or-m"]
    return service


def _tier(answer):
    def call(prompt, system_prompt, result=None):
        return answer
    return MagicMock(side_effect=call)


@pytest.mark.parametrize("answers, expected_provider, expected_attempts", [
    (("tier one answer", None, None), "groq", ["groq"]),
    ((None, "tier two answer", None), "gemini", ["groq", "gemini"]),
    ((None, None, "tier three answer"), "openrouter", ["groq", "gemini", "openrouter"]),
])
def test_each_llm_tier_is_used_only_when_the_previous_tiers_fail(caplog, answers, expected_provider, expected_attempts):
    service = _three_tier_service()
    groq, gemini, openrouter = (_tier(a) for a in answers)
    with patch.object(settings, "LLM_PROVIDER", "groq"), \
            patch.object(service, "_call_groq", groq), \
            patch.object(service, "_call_gemini", gemini), \
            patch.object(service, "_call_openrouter", openrouter), \
            caplog.at_level(logging.INFO, logger="backend.app.services.llm_service"):
        result = service.generate_answer_result(SIMPLE_QUESTION, [])

    expected_text = next(a for a in answers if a)
    assert result.available is True
    assert result.text == expected_text
    assert result.provider == expected_provider
    assert result.providers_attempted == expected_attempts
    # Later tiers are never called once one tier has answered.
    calls = {"groq": groq, "gemini": gemini, "openrouter": openrouter}
    for provider, mock in calls.items():
        assert mock.call_count == (1 if provider in expected_attempts else 0)
    # Every tier receives the same, unchanged prompt (question and context preserved).
    prompts = {mock.call_args.args[0] for mock in calls.values() if mock.called}
    assert len(prompts) == 1 and SIMPLE_QUESTION in prompts.pop()
    tier_number = expected_attempts.index(expected_provider) + 1
    assert f"Answer generated by LLM tier {tier_number} ({expected_provider}," in caplog.text


def test_authentication_error_skips_every_model_of_that_provider():
    now = [0.0]
    cooldowns = ModelCooldowns(clock=lambda: now[0])
    error = RuntimeError("Error code: 401 - Invalid API Key")
    error.status_code = 401

    cooldowns.record_failure("groq", "model-a", error)

    assert cooldowns.available("groq", "model-b") is False
    assert cooldowns.available("gemini", "gemini-m") is True
    now[0] = ModelCooldowns.AUTH_ERROR_SECONDS + 1
    assert cooldowns.available("groq", "model-b") is True


def test_request_specific_403_does_not_disable_the_whole_provider():
    cooldowns = ModelCooldowns(clock=lambda: 0.0)
    error = RuntimeError("Error code: 403 - Your input was flagged by moderation")
    error.status_code = 403

    cooldowns.record_failure("openrouter", "or-a", error)

    assert cooldowns.available("openrouter", "or-b") is True
    assert ModelCooldowns.is_auth_error(error) is False
    assert ModelCooldowns.is_auth_error(RuntimeError("PermissionDenied: API key not valid")) is True


def test_rejected_api_key_is_not_retried_for_the_remaining_models():
    service = _three_tier_service()
    service.GROQ_MODELS = ["groq-a", "groq-b", "groq-c"]
    error = RuntimeError("Error code: 401 - Invalid API Key")
    error.status_code = 401
    client = MagicMock()
    client.chat.completions.create.side_effect = error

    with patch.object(llm_module, "model_cooldowns", ModelCooldowns()), \
            patch("groq.Groq", return_value=client), \
            patch.object(service, "_prepare_external_prompts", side_effect=lambda p, m, prompt, system: (prompt, system)):
        meta = GenerationResult()
        assert service._call_groq("prompt", "system", result=meta) is None
        assert service._call_groq("prompt", "system", result=GenerationResult()) is None

    assert client.chat.completions.create.call_count == 1
    assert meta.failure_category == "auth_error"


# ---------------------------------------------------------------- web search after all LLM tiers

def _all_tiers_fail(*args, result: GenerationResult, **kwargs):
    result.available = False
    result.failure_category = "provider_failed"
    result.providers_attempted = ["groq", "gemini", "openrouter"]
    result.text = UNAVAILABLE_RESPONSE
    return UNAVAILABLE_RESPONSE


def _run(query, *, stream: bool):
    if stream:
        events = list(rag_service.stream_query(db=MagicMock(), query=query))
        streamed = "".join(e["content"] for e in events if e["type"] == "token")
        done = events[-1]
        assert done["type"] == "done"
        assert streamed == done["answer"]
        return done
    return rag_service.process_query(db=MagicMock(), query=query)


@pytest.mark.parametrize("stream", [False, True])
def test_all_llm_tiers_failing_answers_from_web_search_with_links(stream):
    with offline_rag(rows=BRIM_ROWS):
        with patch.object(settings, "WEB_FALLBACK_ENABLED", True), \
                patch("backend.app.services.rag_service.llm_service.generate_answer", side_effect=_all_tiers_fail), \
                patch("backend.app.services.rag_service.web_search_service.search_sap_authoritative",
                      return_value=[WEB_PASSAGE]) as web_search:
            result = _run(SIMPLE_QUESTION, stream=stream)

    web_search.assert_called_once()
    assert result["answer"].startswith(WEB_FALLBACK_INTRO)
    assert f"[{WEB_PASSAGE['title']}]({WEB_PASSAGE['url']})" in result["answer"]
    # Only the sentences that address the question are quoted.
    assert "SAP BRIM covers subscription order management, charging, invoicing and contract accounting." in result["answer"]
    assert "Unrelated navigation text" not in result["answer"]
    assert result["source_type"] == "web"
    assert result["verification_status"] == "unverified"
    assert result["grounding_score"] is None
    assert result["external_search_used"] is True
    assert [w["url"] for w in result["web_sources"]] == [WEB_PASSAGE["url"]]
    assert UNAVAILABLE_RESPONSE not in result["answer"]
    # Knowledge-base text is never pasted into the answer.
    assert "provider contracts" not in result["answer"]


def test_web_fallback_quotes_prose_only_and_skips_pages_that_do_not_address_the_question():
    # Shapes seen in live Tavily results for COMPLEX_QUESTION: link lists, log-on links, TOC leaders,
    # a replacement character, and a page about something else.
    guide = {
        "source_type": "web", "title": "Getting Started Guide", "domain": "help.sap.com",
        "url": "https://help.sap.com/doc/guide.pdf",
        "snippet": "[SAP BRIM Solutions](https://help.sap.com/a) [Log On](https://help.sap.com/http.svc/login?x=1)",
        "chunk_text": (
            "Getting Started Guide\n7 2.2 What�s New in this Document ........ 7 2.3 What is SAP CC? "
            "Our integration guides are a central starting point for the integration of the components that "
            "compose SAP Billing and Revenue Innovation Management (BRIM), such as SAP Convergent Charging."
        ),
    }
    unrelated = {
        "source_type": "web", "title": "Actions and Functions", "domain": "help.sap.com",
        "url": "https://help.sap.com/docs/graph/actions-and-functions",
        "snippet": ": Products SAP Learning Journeys What's New Explore SAP. Actions and Functions.",
        "chunk_text": (
            "Actions and Functions\nActions and functions provide a way to introduce server-side behaviors "
            "into the service."
        ),
    }

    answer = rag_service._web_fallback_answer(COMPLEX_QUESTION, [unrelated, guide])

    assert "1. **[Getting Started Guide](https://help.sap.com/doc/guide.pdf)**" in answer
    assert "Our integration guides are a central starting point" in answer
    for noise in ("Log On", "....", "�", "What is SAP CC?", "Explore SAP", "Actions and Functions", "http.svc"):
        assert noise not in answer


@pytest.mark.parametrize("search", [
    {"return_value": []},
    {"side_effect": RuntimeError("tavily down")},
])
def test_all_methods_failing_returns_a_clear_error(search):
    with offline_rag(rows=BRIM_ROWS):
        with patch.object(settings, "WEB_FALLBACK_ENABLED", True), \
                patch("backend.app.services.rag_service.llm_service.generate_answer", side_effect=_all_tiers_fail), \
                patch("backend.app.services.rag_service.web_search_service.search_sap_authoritative", **search):
            result = _run(SIMPLE_QUESTION, stream=False)

    assert result["answer"] == ALL_METHODS_UNAVAILABLE_RESPONSE
    assert result["verification_status"] == "unavailable"
    assert result["source_type"] == "unavailable"
    assert result["diagnostics"]["failure_category"] == "provider_failed"


def test_disabled_web_fallback_is_not_called_after_llm_failure():
    with offline_rag(rows=BRIM_ROWS):
        with patch.object(settings, "WEB_FALLBACK_ENABLED", False), \
                patch("backend.app.services.rag_service.llm_service.generate_answer", side_effect=_all_tiers_fail), \
                patch("backend.app.services.rag_service.web_search_service.search_sap_authoritative") as web_search:
            result = _run(SIMPLE_QUESTION, stream=False)

    web_search.assert_not_called()
    assert result["answer"] == ALL_METHODS_UNAVAILABLE_RESPONSE


# ---------------------------------------------------------------- grounding rejection (the observed bug)

def _rejected(**overrides):
    verification = {
        "grounding_score": 0.62, "passes_grounding_gate": False, "verification_status": "partial",
        "claims": [], "supported_claims": [], "unsupported_claims": ["SAP BRIM has four component types."],
        "contradicted_claims": [], "critical_unsupported_claims": [], "uncited_standard_ids": ["SOM"],
        "critical_failures": [],
    }
    verification.update(overrides)
    return verification


@pytest.mark.parametrize("stream", [False, True])
def test_grounding_rejection_publishes_labelled_answer_instead_of_generic_failure(stream):
    with offline_rag(answer=SIMPLE_ANSWER, rows=BRIM_ROWS) as calls:
        with patch("backend.app.services.rag_service.grounding_service.verify_answer", return_value=_rejected()):
            result = _run(SIMPLE_QUESTION, stream=stream)

    assert calls["generate"] == 1
    assert result["answer"] != UNAVAILABLE_RESPONSE
    assert result["answer"].startswith("SAP BRIM consists of four main components")
    assert UNVERIFIED_ANSWER_NOTE in result["answer"]
    assert result["verification_status"] in ("partial", "unverified")
    assert result["source_type"] == "knowledge_base"


def test_unconfirmed_identifiers_are_removed_before_an_unverified_answer_is_published():
    fabricated = "Run transaction ZBRIM42 to list all component types."
    answer = f"{SIMPLE_ANSWER} {fabricated}"
    verification = _rejected(
        critical_unsupported_claims=["ZBRIM42"],
        claims=[{"claim": fabricated, "status": "unsupported", "unsupported_technical_ids": ["ZBRIM42"]}],
    )
    with offline_rag(answer=answer, rows=BRIM_ROWS):
        with patch("backend.app.services.rag_service.grounding_service.verify_answer", return_value=verification):
            result = _run(SIMPLE_QUESTION, stream=False)

    assert "ZBRIM42" not in result["answer"]
    assert "Convergent Charging rates usage events" in result["answer"]
    assert result["verification_status"] in ("partial", "unverified")


def test_unverified_web_backed_answer_lists_its_web_sources():
    with offline_rag(answer=SIMPLE_ANSWER, rows=BRIM_ROWS):
        with patch.object(settings, "AUTO_MULTI_SOURCE_FALLBACK", True), \
                patch.object(settings, "WEB_FALLBACK_ENABLED", True), \
                patch("backend.app.services.rag_service.evidence_selection_service.compute_internal_confidence",
                      return_value={"confidence": 0.92, "should_trigger_tavily": False, "signals": {}}), \
                patch("backend.app.services.rag_service.web_search_service.search_sap_authoritative",
                      return_value=[WEB_PASSAGE]), \
                patch("backend.app.services.rag_service.grounding_service.verify_answer", return_value=_rejected()):
            result = _run(SIMPLE_QUESTION, stream=False)

    assert UNVERIFIED_ANSWER_NOTE in result["answer"]
    assert f"[{WEB_PASSAGE['title']}]({WEB_PASSAGE['url']})" in result["answer"]
    assert result["verification_status"] != "verified"


# ---------------------------------------------------------------- answer quality with the real verifier

def test_simple_sap_brim_question_gets_a_verified_direct_answer():
    with offline_rag(answer=SIMPLE_ANSWER, rows=BRIM_ROWS):
        result = _run(SIMPLE_QUESTION, stream=False)

    assert result["answer"].startswith("SAP BRIM consists of four main components")
    assert result["verification_status"] == "verified"
    assert UNVERIFIED_ANSWER_NOTE not in result["answer"]


@pytest.mark.parametrize("stream", [False, True])
def test_complex_components_question_keeps_its_structured_answer(stream):
    with offline_rag(answer=COMPLEX_ANSWER, rows=BRIM_ROWS):
        result = _run(COMPLEX_QUESTION, stream=stream)

    for heading in ("## Subscription Order Management", "## Convergent Charging",
                    "## Convergent Invoicing", "## Contract Accounts Receivable and Payable"):
        assert heading in result["answer"]
    assert result["verification_status"] in ("verified", "partial", "unverified")
    assert UNAVAILABLE_RESPONSE not in result["answer"]
    assert ALL_METHODS_UNAVAILABLE_RESPONSE not in result["answer"]
