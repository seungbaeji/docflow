"""Document tools exposed to the internal agent runtime.

These tools do not perform workflow preparation or session lookup.
They read only from explicit, already-prepared `DocumentAgentToolContext`.
"""

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
    """Return the prepared document identity for the current agent turn.

    This tool is intentionally read-only. It does not resolve the current
    document from session state; it simply exposes the `source_ref_id` and
    basic file metadata that workflow preparation has already selected.
    """
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
    """Return prepared parse metadata for the selected document.

    The agent can call this to inspect what parsing already produced, such as
    page count, parsed unit references, and short unit summaries. The tool
    does not trigger parsing itself.
    """
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
    """Return the deterministic summary prepared for the selected document.

    This exposes the same summary the fallback path can use, together with
    enough metadata for the agent to ground its final answer in the prepared
    document payload.
    """
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
    """Return the prepared payload needed to answer a document question.

    The tool packages the explicit user question together with the prepared
    document payload. A later agent step can turn this structured result into
    the final natural-language answer.
    """
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
