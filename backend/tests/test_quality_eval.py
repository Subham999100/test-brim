"""Offline tests for the phase-0 answer-quality evaluation (backend/evaluation/quality_eval.py, quality_judge.py).
No database, no provider calls: the pipeline and the judge are fakes."""

import json
from pathlib import Path

import pytest

from backend.evaluation import quality_eval as qe
from backend.evaluation import quality_judge as qj

DATASET = Path(__file__).resolve().parents[1] / "evaluation" / "datasets" / "quality_eval_v1.jsonl"


# ---------------------------------------------------------------- dataset

def test_dataset_covers_every_question_type_and_follow_ups():
    cases = qe.load_cases(DATASET)
    types = {case["type"] for case in cases}
    assert {"conceptual", "functional", "technical", "configuration", "troubleshooting", "integration"} <= types
    assert {"hallucination_trap", "false_premise", "out_of_scope", "conversation"} <= types
    follow_ups = [turn for case in cases for turn in case["turns"][1:]]
    assert len(follow_ups) >= 5 and all(turn.get("follow_up_topic") for turn in follow_ups)
    assert len({case["id"] for case in cases}) == len(cases)


@pytest.mark.parametrize("bad", [
    {"id": "x", "type": "conceptual", "turns": []},
    {"id": "x", "type": "conceptual", "turns": [{"query": "q", "expect": "answer", "key_points": []}]},
    {"id": "x", "type": "conceptual", "turns": [{"query": "q", "expect": "guess", "key_points": ["k"]}]},
])
def test_invalid_cases_are_rejected(tmp_path, bad):
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(bad) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        qe.load_cases(path)


# ---------------------------------------------------------------- judge prompt and parsing

def test_judge_prompt_contains_question_history_points_answer_and_numbered_passages():
    prompt = qj.build_judge_prompt(
        query="Which transactions are used?", expect="answer", key_points=["Names FPVA", "Names FPVB"],
        answer="Use FPVA and FPVB.", evidence=[{"document_name": "FI-CA Guide", "chunk_text": "FPVA dunning proposal " * 80}],
        history=[{"role": "user", "content": "Explain dunning in FI-CA."}], follow_up_topic="dunning in FI-CA",
    )
    for text in ("Which transactions are used?", "Explain dunning in FI-CA.", "1. Names FPVA", "2. Names FPVB",
                 "Use FPVA and FPVB.", "[P1] FI-CA Guide", "dunning in FI-CA"):
        assert text in prompt
    assert len(prompt) < 12000, "passages are truncated"


def test_judge_sees_as_much_of_each_passage_as_the_model_did():
    # The model receives up to 1,200 characters per document passage and 1,800 per web passage; a judge that
    # saw less marked supported claims as unsupported (smoke run 2026-11-04).
    passage = "x" * 1700 + " SENTINEL"
    prompt = qj.build_judge_prompt(query="q", expect="answer", key_points=["k"], answer="a",
                                   evidence=[{"document_name": "D", "chunk_text": passage}])
    assert "SENTINEL" in prompt


def test_judge_is_told_that_a_missing_citation_is_not_a_fabrication():
    prompt = qj.build_judge_prompt(query="q", expect="answer", key_points=["k"], answer="a", evidence=[])
    assert "not merely because the passages do not mention it" in prompt


def test_judge_output_is_parsed_from_fenced_json_and_sized_to_the_case():
    raw = '```json\n{"correctness": 4, "key_points": [true, false, true], "fabricated_claims": ["X"],' \
          ' "addresses_question": true, "continuity": null, "verbatim_copy": false, "passage_relevance": [true]}\n```'
    parsed = qj.parse_judge_output(raw, n_key_points=2, n_passages=3)
    assert parsed["correctness"] == 4
    assert parsed["key_points"] == [True, False], "extra entries dropped"
    assert parsed["passage_relevance"] == [True, False, False], "missing entries count as not relevant"
    assert parsed["fabricated_claims"] == ["X"]


@pytest.mark.parametrize("raw", ["", "no json here", '{"correctness": 9, "key_points": []}', '{"key_points": [true]}'])
def test_unusable_judge_output_is_rejected(raw):
    assert qj.parse_judge_output(raw, n_key_points=1, n_passages=0) is None


# ---------------------------------------------------------------- identifiers

def test_identifiers_are_supported_by_evidence_or_an_exact_registry_entry_only():
    answer = "Run transaction FPVA, check table DFKKOP and use transaction ZZFAKE1 on table DFKKOP_FAKE."
    support = qe.identifier_support(answer, ["The dunning proposal FPVA ..."], registry={"dfkkop"})
    assert set(support["identifiers"]) >= {"FPVA", "DFKKOP", "ZZFAKE1", "DFKKOP_FAKE"}
    assert set(support["unsupported"]) == {"ZZFAKE1", "DFKKOP_FAKE"}, "a registry prefix is not a match"


# ---------------------------------------------------------------- run loop and aggregation

class FakePipeline:
    def __init__(self, answers):
        self.answers = list(answers)
        self.histories = []

    def __call__(self, query, history):
        self.histories.append([dict(item) for item in history])
        answer, model = self.answers.pop(0)
        return {
            "answer": answer, "model": model, "provider": "groq", "verification_status": "verified",
            "source_type": "knowledge_base", "evidence": [{"document_name": "Doc", "chunk_text": "FPVA"}],
            "elapsed_ms": 1000.0, "tokens_used": 1500, "resolved_query": query,
            "diagnostics": {"is_truncated": False, "estimated_input_tokens": 4000},
        }


class FakeJudge:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return json.dumps(self.outputs.pop(0))


CONVERSATION = {"id": "conv", "type": "conversation", "modules": [], "turns": [
    {"query": "Explain dunning in FI-CA.", "expect": "answer", "key_points": ["proposal and activity runs"]},
    {"query": "Ok, which transactions are used?", "expect": "answer", "follow_up_topic": "dunning",
     "key_points": ["FPVA", "FPVB"]},
]}


def test_run_carries_the_conversation_and_records_every_turn():
    pipeline = FakePipeline([("Dunning runs ...", "openai/gpt-oss-120b"), ("FPVA and ZZFAKE1", "allam-2-7b")])
    judge = FakeJudge([
        {"correctness": 5, "key_points": [True], "fabricated_claims": [], "addresses_question": True,
         "continuity": None, "verbatim_copy": False, "passage_relevance": [True]},
        {"correctness": 2, "key_points": [True, False], "fabricated_claims": ["ZZFAKE1 is a dunning transaction"],
         "addresses_question": True, "continuity": True, "verbatim_copy": False, "passage_relevance": [False]},
    ])
    records = qe.run_cases([CONVERSATION], pipeline, judge, pause_seconds=0, weak_models={"allam-2-7b"})

    assert [r["turn"] for r in records] == [1, 2]
    assert pipeline.histories[0] == []
    assert pipeline.histories[1] == [
        {"role": "user", "content": "Explain dunning in FI-CA."},
        {"role": "assistant", "content": "Dunning runs ..."},
    ]
    assert records[1]["weak_model"] is True and records[0]["weak_model"] is False
    assert records[1]["unsupported_identifiers"] == ["ZZFAKE1"]
    assert records[1]["is_follow_up"] is True
    assert records[0]["diagnostics"] == {"is_truncated": False, "estimated_input_tokens": 4000}


def _record(**overrides):
    base = {"case_id": "c", "type": "conceptual", "turn": 1, "expect": "answer", "is_follow_up": False,
            "correctness": 4, "key_points": [True, False], "fabricated_claims": [], "unsupported_identifiers": [],
            "passage_relevance": [True, True, False, False], "continuity": None, "verbatim_copy": False,
            "weak_model": False, "unavailable": False, "elapsed_ms": 1000.0, "tokens_used": 1000, "judge_ok": True}
    base.update(overrides)
    return base


def test_aggregate_reports_the_quality_metrics():
    summary = qe.aggregate([
        _record(),
        _record(type="technical", correctness=2, key_points=[False, False], unsupported_identifiers=["ZZ1"],
                weak_model=True, elapsed_ms=3000.0, tokens_used=3000),
        _record(type="conversation", turn=2, is_follow_up=True, continuity=False, fabricated_claims=["x"]),
        _record(type="hallucination_trap", expect="no_fabrication", key_points=[True], correctness=5,
                passage_relevance=[]),
        _record(type="out_of_scope", expect="refuse", key_points=[False], correctness=1, passage_relevance=[]),
    ])
    assert summary["turns"] == 5
    assert summary["answer_turns"] == 3
    assert summary["correctness_mean"] == pytest.approx((4 + 2 + 4) / 3, abs=0.01)
    assert summary["key_point_coverage"] == pytest.approx((0.5 + 0 + 0.5) / 3, abs=0.01)
    assert summary["hallucination_rate"] == pytest.approx(2 / 5)
    assert summary["retrieval_precision"] == pytest.approx(0.5)
    assert summary["continuity_rate"] == 0.0
    assert summary["behaviour_pass_rate"] == pytest.approx(0.5), "trap passed, refusal failed"
    assert summary["weak_model_rate"] == pytest.approx(1 / 5)
    assert summary["latency_p50_ms"] == 1000.0
    assert set(summary["by_type"]) == {"conceptual", "technical", "conversation", "hallucination_trap", "out_of_scope"}


def test_aggregate_skips_turns_the_judge_could_not_score():
    summary = qe.aggregate([_record(), _record(judge_ok=False, correctness=None, key_points=[])])
    assert summary["judged_turns"] == 1 and summary["correctness_mean"] == 4.0


# ---------------------------------------------------------------- two-step runs: generate first, judge later

def test_records_keep_the_evidence_so_turns_can_be_rejudged():
    pipeline = FakePipeline([("Dunning runs ...", "qwen"), ("FPVA", "qwen")])
    records = qe.run_cases([CONVERSATION], pipeline, None, pause_seconds=0)
    assert records[0]["evidence"] == [{"document_name": "Doc", "chunk_text": "FPVA"}]
    assert all(r["judge_ok"] is False and r["correctness"] is None for r in records), "no judge, no scores"


def test_rejudge_scores_stored_turns_with_their_conversation_history():
    records = qe.run_cases([CONVERSATION], FakePipeline([("Dunning runs ...", "qwen"), ("FPVA", "qwen")]), None,
                           pause_seconds=0)
    judge = FakeJudge([
        {"correctness": 5, "key_points": [True], "fabricated_claims": [], "addresses_question": True,
         "continuity": None, "verbatim_copy": False, "passage_relevance": [True]},
        {"correctness": 3, "key_points": [True, False], "fabricated_claims": [], "addresses_question": True,
         "continuity": True, "verbatim_copy": False, "passage_relevance": [True]},
    ])
    rejudged = qe.rejudge(records, [CONVERSATION], judge, pause_seconds=0)

    assert [r["correctness"] for r in rejudged] == [5, 3]
    assert rejudged[1]["continuity"] is True and rejudged[1]["key_points"] == [True, False]
    assert "Explain dunning in FI-CA." in judge.prompts[1] and "Dunning runs ..." in judge.prompts[1]
    assert records[0]["correctness"] is None, "the stored run is not modified"


@pytest.mark.parametrize("message, seconds", [
    ("Rate limit reached ... Please try again in 7.5s. Need more tokens?", 7.5),
    ("Please try again in 1m2.5s.", 62.5),
    ("quota exceeded", 20.0),
])
def test_judge_waits_as_long_as_the_provider_asks(message, seconds):
    assert qj.retry_after_seconds(message) == seconds
