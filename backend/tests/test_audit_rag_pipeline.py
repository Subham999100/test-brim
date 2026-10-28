"""Audit regressions for the RAG orchestrator (AUDIT_REPORT.md F-02, F-03, F-04, F-27). Offline only."""

from unittest.mock import MagicMock

from backend.app.services.rag_service import rag_service
from backend.tests.offline_rag import RAG_QUESTION, offline_rag


def test_f02_process_query_completes_retrieval_backed_answer():
    """process_query used undefined names in its diagnostics and raised NameError after generation."""
    with offline_rag() as calls:
        result = rag_service.process_query(db=MagicMock(), query=RAG_QUESTION)

    assert calls["retrieve"] >= 1, "question must go through retrieval"
    assert "posting area" in result["answer"].lower()
    assert result["citations"], "knowledge-base citations are built"
    diagnostics = result["diagnostics"]
    assert diagnostics["retrieved_chunks_count"] == 2
    assert diagnostics["final_context_chunks_count"] >= 1
    assert isinstance(diagnostics["post_processing_modified"], bool)
