from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, tool

from docflow_agent.errors import DocumentAgentRuntimeError
from docflow_agent.ports.session_context import SessionDocumentStore
from docflow_agent.usecases.document_workflow import RepositoryBackedDocumentUsecases


class AnswerAboutCurrentDocumentArgs(BaseModel):
    question: str = Field(min_length=1)


def build_document_agent_tools(
    *,
    session_id: str,
    session_document_store: SessionDocumentStore,
    document_usecases: RepositoryBackedDocumentUsecases,
) -> dict[str, BaseTool]:
    def require_source_ref() -> str:
        source_ref_id = session_document_store.get_current_source_ref(session_id)
        if source_ref_id is None:
            raise DocumentAgentRuntimeError("no current document is associated with the session")
        return source_ref_id

    @tool("get_current_document")
    def get_current_document() -> dict[str, object]:
        """Return the current uploaded document metadata for the active session."""
        source_ref_id = require_source_ref()
        payload = document_usecases.build_document_payload(source_ref_id=source_ref_id)
        return {
            "source_ref_id": payload["source_ref_id"],
            "source_type": payload["source_type"],
            "file_name": payload["file_name"],
            "file_path": payload["file_path"],
        }

    @tool("parse_current_document")
    def parse_current_document() -> dict[str, object]:
        """Ensure the current document is parsed and return parsed unit metadata."""
        source_ref_id = require_source_ref()
        payload = document_usecases.build_document_payload(source_ref_id=source_ref_id)
        return {
            "source_ref_id": payload["source_ref_id"],
            "page_count": payload["page_count"],
            "unit_count": payload["unit_count"],
            "parsed_unit_ref_ids": payload["parsed_unit_ref_ids"],
            "unit_summaries": payload["unit_summaries"],
        }

    @tool("summarize_current_document")
    def summarize_current_document() -> dict[str, object]:
        """Return a deterministic summary payload for the current document."""
        source_ref_id = require_source_ref()
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

    @tool("answer_about_current_document", args_schema=AnswerAboutCurrentDocumentArgs)
    def answer_about_current_document(question: str) -> dict[str, object]:
        """Return the current document payload for answering a specific question."""
        source_ref_id = require_source_ref()
        payload = document_usecases.build_document_payload(source_ref_id=source_ref_id)
        return {
            "source_ref_id": payload["source_ref_id"],
            "question": question,
            "payload": payload,
        }

    tools = [
        get_current_document,
        parse_current_document,
        summarize_current_document,
        answer_about_current_document,
    ]
    return {tool_item.name: tool_item for tool_item in tools}
