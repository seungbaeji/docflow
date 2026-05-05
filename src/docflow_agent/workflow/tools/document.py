from __future__ import annotations

from docflow_agent.errors import DocumentAgentRuntimeError
from docflow_agent.ports.session_context import SessionDocumentStore
from docflow_agent.types.value.document_agent import DocumentAgentTool
from docflow_agent.usecases.document_workflow import RepositoryBackedDocumentUsecases


def build_document_agent_tools(
    *,
    session_document_store: SessionDocumentStore,
    document_usecases: RepositoryBackedDocumentUsecases,
) -> dict[str, DocumentAgentTool]:
    def get_current_document(arguments: dict[str, object], session_id: str) -> dict[str, object]:
        del arguments
        source_ref_id = _require_source_ref(session_document_store, session_id)
        payload = document_usecases.build_document_payload(source_ref_id=source_ref_id)
        return {
            "source_ref_id": payload["source_ref_id"],
            "source_type": payload["source_type"],
            "file_name": payload["file_name"],
            "file_path": payload["file_path"],
        }

    def parse_current_document(arguments: dict[str, object], session_id: str) -> dict[str, object]:
        del arguments
        source_ref_id = _require_source_ref(session_document_store, session_id)
        payload = document_usecases.build_document_payload(source_ref_id=source_ref_id)
        return {
            "source_ref_id": payload["source_ref_id"],
            "page_count": payload["page_count"],
            "unit_count": payload["unit_count"],
            "parsed_unit_ref_ids": payload["parsed_unit_ref_ids"],
            "unit_summaries": payload["unit_summaries"],
        }

    def summarize_current_document(arguments: dict[str, object], session_id: str) -> dict[str, object]:
        del arguments
        source_ref_id = _require_source_ref(session_document_store, session_id)
        payload = document_usecases.build_document_payload(source_ref_id=source_ref_id)
        return {
            "source_ref_id": payload["source_ref_id"],
            "summary": document_usecases.summarize_source_ref(source_ref_id),
            "source_type": payload["source_type"],
            "file_name": payload["file_name"],
            "page_count": payload["page_count"],
            "unit_count": payload["unit_count"],
            "unit_summaries": payload["unit_summaries"],
        }

    def answer_about_current_document(
        arguments: dict[str, object],
        session_id: str,
    ) -> dict[str, object]:
        source_ref_id = _require_source_ref(session_document_store, session_id)
        question = arguments.get("question")
        if not isinstance(question, str) or not question.strip():
            raise DocumentAgentRuntimeError(
                "answer_about_current_document requires a non-empty question argument"
            )
        payload = document_usecases.build_document_payload(source_ref_id=source_ref_id)
        return {
            "source_ref_id": payload["source_ref_id"],
            "question": question,
            "payload": payload,
        }

    return {
        "get_current_document": DocumentAgentTool(
            name="get_current_document",
            description="Return the current uploaded document metadata for the active session.",
            invoke=get_current_document,
        ),
        "parse_current_document": DocumentAgentTool(
            name="parse_current_document",
            description="Ensure the current document is parsed and return parsed unit metadata.",
            invoke=parse_current_document,
        ),
        "summarize_current_document": DocumentAgentTool(
            name="summarize_current_document",
            description="Return a deterministic summary payload for the current document.",
            invoke=summarize_current_document,
        ),
        "answer_about_current_document": DocumentAgentTool(
            name="answer_about_current_document",
            description="Return the current document payload for answering a specific question.",
            invoke=answer_about_current_document,
        ),
    }


def _require_source_ref(
    session_document_store: SessionDocumentStore,
    session_id: str,
) -> str:
    source_ref_id = session_document_store.get_current_source_ref(session_id)
    if source_ref_id is None:
        raise DocumentAgentRuntimeError("no current document is associated with the session")
    return source_ref_id
