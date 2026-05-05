from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from langchain.tools import BaseTool, ToolRuntime, tool

from docflow_agent.errors import DocumentAgentRuntimeError
from docflow_agent.types.value.document import DocumentPayload
from docflow_agent.types.value.document_agent import (
    CurrentDocumentMetadataResult,
    CurrentDocumentParseResult,
    CurrentDocumentQuestionResult,
    CurrentDocumentSummaryResult,
)


@dataclass(frozen=True)
class DocumentAgentToolContext:
    session_id: str


def bind_document_agent_tools(
    *,
    build_document_payload: Callable[[str], DocumentPayload],
    summarize_source_ref: Callable[[str], str],
) -> dict[str, BaseTool]:
    def require_source_ref(runtime: ToolRuntime[DocumentAgentToolContext]) -> str:
        if runtime.store is None:
            raise DocumentAgentRuntimeError("no runtime store is available for document tools")
        item = runtime.store.get(
            ("session_documents", runtime.context.session_id),
            "current_source_ref",
        )
        if item is None:
            raise DocumentAgentRuntimeError("no current document is associated with the session")
        source_ref_id = item.value.get("source_ref_id")
        if not isinstance(source_ref_id, str):
            raise DocumentAgentRuntimeError("runtime store returned an invalid source reference")
        return source_ref_id

    @tool
    def get_current_document(
        runtime: ToolRuntime[DocumentAgentToolContext],
    ) -> CurrentDocumentMetadataResult:
        """Return the current uploaded document metadata for the active session."""
        source_ref_id = require_source_ref(runtime)
        payload = build_document_payload(source_ref_id)
        return CurrentDocumentMetadataResult(
            source_ref_id=payload.source_ref_id,
            source_type=payload.source_type,
            file_name=payload.file_name,
            file_path=payload.file_path,
        )

    @tool
    def parse_current_document(
        runtime: ToolRuntime[DocumentAgentToolContext],
    ) -> CurrentDocumentParseResult:
        """Ensure the current document is parsed and return parsed unit metadata."""
        source_ref_id = require_source_ref(runtime)
        payload = build_document_payload(source_ref_id)
        return CurrentDocumentParseResult(
            source_ref_id=payload.source_ref_id,
            page_count=payload.page_count,
            unit_count=payload.unit_count,
            parsed_unit_ref_ids=list(payload.parsed_unit_ref_ids),
            unit_summaries=list(payload.unit_summaries),
        )

    @tool
    def summarize_current_document(
        runtime: ToolRuntime[DocumentAgentToolContext],
    ) -> CurrentDocumentSummaryResult:
        """Return a deterministic summary payload for the current document."""
        source_ref_id = require_source_ref(runtime)
        payload = build_document_payload(source_ref_id)
        return CurrentDocumentSummaryResult(
            source_ref_id=payload.source_ref_id,
            summary=summarize_source_ref(source_ref_id),
            source_type=payload.source_type,
            file_name=payload.file_name,
            page_count=payload.page_count,
            unit_count=payload.unit_count,
            unit_summaries=list(payload.unit_summaries),
        )

    @tool
    def answer_about_current_document(
        question: str,
        runtime: ToolRuntime[DocumentAgentToolContext],
    ) -> CurrentDocumentQuestionResult:
        """Return the current document payload for answering a specific question."""
        source_ref_id = require_source_ref(runtime)
        payload = build_document_payload(source_ref_id)
        return CurrentDocumentQuestionResult(
            source_ref_id=payload.source_ref_id,
            question=question,
            payload=payload,
        )

    tools = [
        get_current_document,
        parse_current_document,
        summarize_current_document,
        answer_about_current_document,
    ]
    return {tool_item.name: tool_item for tool_item in tools}
