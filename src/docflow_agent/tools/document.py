from __future__ import annotations

from langchain.tools import BaseTool, ToolRuntime, tool

from docflow_agent.types.value.document_agent import (
    CurrentDocumentMetadataResult,
    CurrentDocumentParseResult,
    CurrentDocumentQuestionResult,
    CurrentDocumentSummaryResult,
    DocumentAgentToolContext,
)


@tool
def get_current_document(
    runtime: ToolRuntime[DocumentAgentToolContext],
) -> CurrentDocumentMetadataResult:
    """Return the prepared current document metadata."""
    payload = runtime.context.document_payload
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
    """Return prepared parsed unit metadata for the current document."""
    payload = runtime.context.document_payload
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
    """Return the prepared summary payload for the current document."""
    payload = runtime.context.document_payload
    return CurrentDocumentSummaryResult(
        source_ref_id=payload.source_ref_id,
        summary=runtime.context.document_summary,
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
    """Return the prepared document payload for answering a specific question."""
    payload = runtime.context.document_payload
    return CurrentDocumentQuestionResult(
        source_ref_id=payload.source_ref_id,
        question=question,
        payload=payload,
    )


DOCUMENT_AGENT_TOOLS: tuple[BaseTool, ...] = (
    get_current_document,
    parse_current_document,
    summarize_current_document,
    answer_about_current_document,
)
