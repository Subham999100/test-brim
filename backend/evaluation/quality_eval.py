"""Phase-0 answer-quality evaluation for Scholar (honest replacement for the legacy baseline metrics).

Runs hand-written SAP BRIM questions and multi-turn conversations through the real Scholar pipeline
(`rag_service.process_query`) against the real knowledge base, then grades every turn with an LLM judge on a
different provider (quality_judge.py). Measures what the model was actually given, never a self-generated gold.

Metrics (see aggregate()): correctness (judge 1-5), key-point coverage, hallucination rate (judge-flagged
fabrications or identifiers found neither in the evidence nor exactly in the identifier registry), retrieval
precision of the passages the model received, conversation continuity on follow-ups, expected-behaviour pass rate
(traps, false premises, refusals), weak-model and unavailable rates, latency and tokens.

Usage (from the repository root, with the database and provider keys of `.env`):
    .venv\\Scripts\\python -m backend.evaluation.quality_eval --label baseline
    .venv\\Scripts\\python -m backend.evaluation.quality_eval --label smoke --limit 2 --pause 5

Results go to backend/evaluation/results/quality_<label>.jsonl and quality_<label>_summary.json; an existing
label is never overwritten (use a new label).
"""

import argparse
import json
import logging
import math
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from backend.evaluation.quality_judge import MAX_PASSAGES, PASSAGE_CHARS, build_judge_prompt, parse_judge_output

EVALUATION_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = EVALUATION_DIR / "datasets" / "quality_eval_v1.jsonl"
RESULTS_DIR = EVALUATION_DIR / "results"
EXPECTATIONS = {"answer", "no_fabrication", "correct_premise", "refuse"}
DEFAULT_WEAK_MODELS = {"allam-2-7b", "liquid/lfm-2.5-2.6b:free"}

logger = logging.getLogger("quality_eval")

# A pipeline call: (query, history) -> {"answer", "model", "provider", "verification_status", "source_type",
#                                       "evidence", "elapsed_ms", "tokens_used", "resolved_query"}
Pipeline = Callable[[str, List[Dict[str, Any]]], Dict[str, Any]]
Judge = Callable[[str], Optional[str]]


# ---------------------------------------------------------------- dataset

def load_cases(path: Path) -> List[Dict[str, Any]]:
    """Cases from a JSONL file, validated so a typo cannot silently skew the metrics."""
    cases, seen = [], set()
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        where = f"{path}:{number}"
        if not case.get("id") or case["id"] in seen:
            raise ValueError(f"{where}: missing or duplicate id")
        seen.add(case["id"])
        turns = case.get("turns")
        if not isinstance(turns, list) or not turns:
            raise ValueError(f"{where}: a case needs at least one turn")
        for turn in turns:
            if not str(turn.get("query") or "").strip():
                raise ValueError(f"{where}: empty query")
            if turn.get("expect") not in EXPECTATIONS:
                raise ValueError(f"{where}: expect must be one of {sorted(EXPECTATIONS)}")
            if not isinstance(turn.get("key_points"), list) or not turn["key_points"]:
                raise ValueError(f"{where}: key_points must be a non-empty list")
        cases.append(case)
    return cases


# ---------------------------------------------------------------- identifiers

def _mentioned(value: str, texts: Iterable[str]) -> bool:
    pattern = re.compile(rf"(?<![A-Za-z0-9_/]){re.escape(value)}(?![A-Za-z0-9_])", re.IGNORECASE)
    return any(pattern.search(text or "") for text in texts)


def identifier_support(answer: str, evidence_texts: List[str], registry: Set[str]) -> Dict[str, List[str]]:
    """SAP identifiers in the answer, and those supported by neither the evidence nor an exact registry entry."""
    from backend.app.services.sap_identifier_validator import extract_identifiers

    identifiers = list(dict.fromkeys(item.value for item in extract_identifiers(answer or "")))
    unsupported = [
        value for value in identifiers
        if value.lower() not in registry and not _mentioned(value, evidence_texts)
    ]
    return {"identifiers": identifiers, "unsupported": unsupported}


# ---------------------------------------------------------------- run

_VERDICT_FIELDS = ("correctness", "key_points", "fabricated_claims", "addresses_question", "continuity",
                   "verbatim_copy", "passage_relevance")


def _verdict_fields(verdict: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if verdict is None:
        return {"judge_ok": False, "correctness": None, "key_points": [], "fabricated_claims": [],
                "addresses_question": None, "continuity": None, "verbatim_copy": None, "passage_relevance": []}
    return {"judge_ok": True, **{field: verdict[field] for field in _VERDICT_FIELDS}}


def _judge_turn(judge: Optional[Judge], turn: Dict[str, Any], answer: str, evidence: List[Dict[str, Any]],
                history: List[Dict[str, Any]]) -> Dict[str, Any]:
    if judge is None:
        return _verdict_fields(None)
    raw = judge(build_judge_prompt(
        query=turn["query"], expect=turn["expect"], key_points=turn["key_points"], answer=answer,
        evidence=evidence, history=history, follow_up_topic=turn.get("follow_up_topic"),
    ))
    return _verdict_fields(parse_judge_output(raw, n_key_points=len(turn["key_points"]), n_passages=len(evidence)))


def _stored_evidence(evidence: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """The passages as the judge needs them, so a run can be graded again later."""
    return [
        {"document_name": str(p.get("document_name") or p.get("title") or p.get("url") or "source"),
         "chunk_text": str(p.get("chunk_text") or p.get("snippet") or "")[:PASSAGE_CHARS]}
        for p in (evidence or [])[:MAX_PASSAGES]
    ]


def run_cases(
    cases: List[Dict[str, Any]],
    pipeline: Pipeline,
    judge: Optional[Judge],
    *,
    pause_seconds: float = 20.0,
    weak_models: Optional[Set[str]] = None,
    registry: Optional[Set[str]] = None,
    on_record: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> List[Dict[str, Any]]:
    """Runs every turn in order, carrying each conversation's history exactly as the chat API passes it."""
    weak = weak_models if weak_models is not None else DEFAULT_WEAK_MODELS
    known = registry if registry is not None else set()
    records: List[Dict[str, Any]] = []
    first_call = True
    for case in cases:
        history: List[Dict[str, Any]] = []
        for index, turn in enumerate(case["turns"], 1):
            if not first_call and pause_seconds:
                time.sleep(pause_seconds)
            first_call = False
            outcome = pipeline(turn["query"], [dict(item) for item in history])
            answer = outcome.get("answer") or ""
            evidence = _stored_evidence(outcome.get("evidence") or [])
            verdict = _judge_turn(judge, turn, answer, evidence, history)
            support = identifier_support(
                answer, [str(p.get("chunk_text") or p.get("snippet") or "") for p in evidence], known
            )
            record = {
                "case_id": case["id"], "type": case["type"], "turn": index, "query": turn["query"],
                "expect": turn["expect"], "is_follow_up": index > 1,
                "resolved_query": outcome.get("resolved_query"),
                "answer": answer, "model": outcome.get("model"), "provider": outcome.get("provider"),
                "weak_model": (outcome.get("model") or "") in weak,
                "verification_status": outcome.get("verification_status"),
                "source_type": outcome.get("source_type"),
                "unavailable": outcome.get("verification_status") == "unavailable" or outcome.get("source_type") == "unavailable",
                "evidence_count": len(evidence),
                "evidence_documents": [p["document_name"] for p in evidence],
                "evidence": evidence,
                "elapsed_ms": outcome.get("elapsed_ms"), "tokens_used": outcome.get("tokens_used"),
                "diagnostics": outcome.get("diagnostics"),
                "identifiers": support["identifiers"], "unsupported_identifiers": support["unsupported"],
                **verdict,
            }
            records.append(record)
            if on_record:
                on_record(record)
            history += [{"role": "user", "content": turn["query"]}, {"role": "assistant", "content": answer}]
    return records


def rejudge(
    records: List[Dict[str, Any]],
    cases: List[Dict[str, Any]],
    judge: Judge,
    *,
    pause_seconds: float = 0.0,
    on_record: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> List[Dict[str, Any]]:
    """Grades stored turns again (same answers and passages), rebuilding each conversation's history.
    Returns new records; the stored ones are not modified."""
    turns = {(case["id"], index): turn for case in cases for index, turn in enumerate(case["turns"], 1)}
    histories: Dict[str, List[Dict[str, Any]]] = {}
    judged = []
    for position, record in enumerate(records):
        if position and pause_seconds:
            time.sleep(pause_seconds)
        turn = turns[(record["case_id"], record["turn"])]
        history = histories.setdefault(record["case_id"], [])
        verdict = _judge_turn(judge, turn, record.get("answer") or "", record.get("evidence") or [], history)
        updated = {**record, **verdict}
        judged.append(updated)
        if on_record:
            on_record(updated)
        history += [{"role": "user", "content": record["query"]},
                    {"role": "assistant", "content": record.get("answer") or ""}]
    return judged


# ---------------------------------------------------------------- metrics

def _mean(values: List[float]) -> Optional[float]:
    return round(statistics.fmean(values), 4) if values else None


def _percentile(values: List[float], fraction: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def _hallucinated(record: Dict[str, Any]) -> bool:
    return bool(record.get("fabricated_claims")) or bool(record.get("unsupported_identifiers"))


def aggregate(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summary metrics; judge-dependent ones use only the turns the judge could score."""
    judged = [r for r in records if r.get("judge_ok")]
    answers = [r for r in judged if r["expect"] == "answer"]
    behaviour = [r for r in judged if r["expect"] != "answer"]
    with_passages = [r for r in judged if r.get("passage_relevance")]
    follow_ups = [r for r in judged if r.get("is_follow_up") and r.get("continuity") is not None]
    latencies = [r["elapsed_ms"] for r in records if isinstance(r.get("elapsed_ms"), (int, float))]
    tokens = [r["tokens_used"] for r in records if isinstance(r.get("tokens_used"), (int, float))]

    summary = {
        "turns": len(records),
        "judged_turns": len(judged),
        "answer_turns": len(answers),
        "correctness_mean": _mean([r["correctness"] for r in answers]),
        "key_point_coverage": _mean([sum(r["key_points"]) / len(r["key_points"]) for r in answers if r["key_points"]]),
        "hallucination_rate": _mean([1.0 if _hallucinated(r) else 0.0 for r in judged]),
        "retrieval_precision": _mean([sum(r["passage_relevance"]) / len(r["passage_relevance"]) for r in with_passages]),
        "continuity_rate": _mean([1.0 if r["continuity"] else 0.0 for r in follow_ups]),
        "behaviour_pass_rate": _mean([
            1.0 if all(r["key_points"]) and not _hallucinated(r) else 0.0 for r in behaviour
        ]),
        "verbatim_copy_rate": _mean([1.0 if r.get("verbatim_copy") else 0.0 for r in answers]),
        "weak_model_rate": _mean([1.0 if r.get("weak_model") else 0.0 for r in records]),
        "unavailable_rate": _mean([1.0 if r.get("unavailable") else 0.0 for r in records]),
        "latency_p50_ms": _percentile(latencies, 0.5),
        "latency_p95_ms": _percentile(latencies, 0.95),
        "tokens_used_mean": _mean(tokens),
        "models": {},
        "by_type": {},
    }
    for record in records:
        model = record.get("model") or "(none)"
        summary["models"][model] = summary["models"].get(model, 0) + 1
    for kind in dict.fromkeys(r["type"] for r in records):
        group = [r for r in judged if r["type"] == kind]
        summary["by_type"][kind] = {
            "turns": len([r for r in records if r["type"] == kind]),
            "correctness_mean": _mean([r["correctness"] for r in group]),
            "hallucination_rate": _mean([1.0 if _hallucinated(r) else 0.0 for r in group]),
        }
    return summary


# ---------------------------------------------------------------- live pipeline (real database and providers)

class ScholarPipeline:
    """The real Scholar pipeline as the chat API runs it, for a regular user in the default access group.
    Captures the passages of the last generation call (the answer the user sees) without changing the code."""

    def __init__(self):
        from types import SimpleNamespace

        from backend.app.config import settings
        from backend.app.database import SessionLocal

        self._db = SessionLocal()
        self._user = SimpleNamespace(id="quality-eval", is_admin=False, groups=[settings.DEFAULT_ACCESS_GROUP])

    def __call__(self, query: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        from unittest.mock import patch

        from backend.app.services import token_meter
        from backend.app.services.llm_service import llm_service
        from backend.app.services.rag_service import rag_service

        calls: List[Dict[str, Any]] = []
        original = llm_service.generate_answer

        def spy(*args, **kwargs):
            evidence = kwargs.get("evidence", args[1] if len(args) > 1 else [])
            calls.append({"query": args[0] if args else kwargs.get("query"), "evidence": list(evidence or [])})
            return original(*args, **kwargs)

        meter = token_meter.TokenMeter()

        def step():
            yield rag_service.process_query(self._db, query, chat_history=history, user=self._user)

        started = time.perf_counter()
        with patch.object(llm_service, "generate_answer", spy):
            try:
                result = next(token_meter.metered(step(), meter))
            except Exception as exc:  # noqa: BLE001 - a crash is a result too
                logger.exception("pipeline failed for %r", query)
                self._db.rollback()
                result = {"answer": "", "verification_status": "unavailable", "source_type": "error",
                          "pipeline_error": type(exc).__name__}
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        last = calls[-1] if calls else {"query": None, "evidence": []}
        diagnostics = result.get("diagnostics") or {}
        return {
            "diagnostics": {key: diagnostics.get(key) for key in (
                "estimated_input_tokens", "configured_output_token_limit", "finish_reason", "is_truncated",
                "was_continued", "failed_over", "providers_attempted", "failure_category",
            )} | {"generation_calls": len(calls), "pipeline_error": result.get("pipeline_error")},
            "answer": result.get("answer") or "",
            "model": result.get("model_used"), "provider": result.get("provider_used"),
            "verification_status": result.get("verification_status"), "source_type": result.get("source_type"),
            "evidence": last["evidence"], "resolved_query": last["query"],
            "elapsed_ms": elapsed, "tokens_used": meter.used_tokens,
        }


def _registry() -> Set[str]:
    from backend.app.services.sap_entity_service import SAP_TECHNICAL_ENTITIES

    return {key.lower() for key in SAP_TECHNICAL_ENTITIES}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True, help="name of this run, e.g. baseline or phase1")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--limit", type=int, default=0, help="only the first N cases")
    parser.add_argument("--pause", type=float, default=20.0, help="seconds between questions (provider limits)")
    parser.add_argument("--judge", choices=("groq", "gemini"), default="groq",
                        help="judge provider; run generation with --no-judge first, then --rejudge")
    parser.add_argument("--judge-model", default="", help="default: openai/gpt-oss-120b (groq), gemini-2.5-flash")
    parser.add_argument("--no-judge", action="store_true", help="generate and store answers only")
    parser.add_argument("--rejudge", default="", metavar="SOURCE_LABEL",
                        help="grade the stored answers of another label instead of generating")
    args = parser.parse_args(argv)

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.label):
        parser.error("label may contain letters, digits, '.', '_' and '-' only")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    records_path = RESULTS_DIR / f"quality_{args.label}.jsonl"
    summary_path = RESULTS_DIR / f"quality_{args.label}_summary.json"
    if records_path.exists() or summary_path.exists():
        parser.error(f"results for label {args.label!r} already exist; choose a new label")

    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from backend.app.config import settings
    from backend.evaluation.quality_judge import GeminiJudge, GroqJudge

    cases = load_cases(Path(args.dataset))
    judge: Optional[Judge] = None
    if not args.no_judge:
        judge = (GroqJudge(settings.GROQ_API_KEY, model=args.judge_model or "openai/gpt-oss-120b")
                 if args.judge == "groq" else
                 GeminiJudge(settings.GEMINI_API_KEY, model=args.judge_model or "gemini-2.5-flash"))
    if args.rejudge and judge is None:
        parser.error("--rejudge needs a judge")

    with records_path.open("w", encoding="utf-8") as out:
        def write(record: Dict[str, Any]) -> None:
            out.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            out.flush()
            print(f"[{record['case_id']} t{record['turn']}] model={record['model']} "
                  f"correctness={record['correctness']} unavailable={record['unavailable']} "
                  f"{record['elapsed_ms']} ms", flush=True)

        if args.rejudge:
            source = RESULTS_DIR / f"quality_{args.rejudge}.jsonl"
            stored = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
            records = rejudge(stored, cases, judge, pause_seconds=args.pause, on_record=write)
        else:
            selected = cases[: args.limit or None]
            records = run_cases(selected, ScholarPipeline(), judge, pause_seconds=args.pause,
                                registry=_registry(), on_record=write)

    summary = aggregate(records)
    summary.update({"label": args.label, "dataset": Path(args.dataset).name,
                    "judge_model": getattr(judge, "model_name", None), "rejudged_from": args.rejudge or None,
                    "pipeline": "scholar (rag_service.process_query)"})
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in {"by_type", "models"}}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
