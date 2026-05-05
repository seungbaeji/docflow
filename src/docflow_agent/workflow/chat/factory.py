"""Workflow assembly helpers for document-aware chat.

This module hides the wiring needed to prepare document context for the agent
runtime. It builds the prep workflow, loads prepared payloads, and exposes
small helpers that higher layers can call without knowing the internal graph.
"""

from __future__ import annotations

from collections.abc import Callable

from langgraph.store.base import BaseStore

from docflow_agent.config.prompt import get_document_agent_system_prompt
from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.ports.session_context import SessionDocumentStore
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.tools import DOCUMENT_AGENT_TOOLS, DocumentAgentToolContext
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument
from docflow_agent.types.value.document import DocumentPayload
from docflow_agent.workflow.agent import AgentRuntime
from docflow_agent.workflow.chat.graph import build_workflow, invoke_workflow
from docflow_agent.workflow.document import chat as document_chat
from docflow_agent.workflow.document import mail as document_mail
from docflow_agent.workflow.document import parse as document_parse
from docflow_agent.workflow.document import source as document_source


def create_prep_workflow(
    *,
    artifact_repository: ArtifactRepository,
    session_document_store: SessionDocumentStore,
    workflow_run_store: WorkflowRunStore,
    vector_store: VectorStorePort,
    pdf_client: OpenDataLoaderPdfClient | None,
    pdf_parser: Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument],
) -> object:
    """Build the prep workflow that turns an upload into prepared artifacts."""
    return build_workflow(
        artifact_repository=artifact_repository,
        session_document_store=session_document_store,
        source_from_upload=lambda upload_id: document_source.source_from_upload(
            artifact_repository,
            upload_id=upload_id,
        ),
        parse_units=lambda source_ref_id: document_parse.parse_units(
            artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        ),
        categorize_units=lambda unit_ref_ids: document_parse.categorize_units(
            artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        combine_bundle=lambda unit_ref_ids: document_parse.combine_bundle(
            artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        analyze=lambda bundle_ref_id: document_mail.analyze(
            artifact_repository,
            bundle_ref_id=bundle_ref_id,
            workflow_run_store=workflow_run_store,
            vector_store=vector_store,
        ),
    )


def prepare_context(
    *,
    artifact_repository: ArtifactRepository,
    session_document_store: SessionDocumentStore,
    workflow_run_store: WorkflowRunStore,
    vector_store: VectorStorePort,
    pdf_client: OpenDataLoaderPdfClient | None,
    pdf_parser: Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument],
    session_id: str,
    message: str,
) -> DocumentAgentToolContext:
    """Prepare explicit tool context for a document-aware chat turn."""
    prep_workflow = create_prep_workflow(
        artifact_repository=artifact_repository,
        session_document_store=session_document_store,
        workflow_run_store=workflow_run_store,
        vector_store=vector_store,
        pdf_client=pdf_client,
        pdf_parser=pdf_parser,
    )
    prep_state = invoke_workflow(
        workflow=prep_workflow,
        session_id=session_id,
        message=message,
    )
    source_ref_id = prep_state["source_ref_id"]
    payload = build_payload(
        artifact_repository=artifact_repository,
        source_ref_id=source_ref_id,
    )
    summary = summarize_ref(
        artifact_repository=artifact_repository,
        source_ref_id=source_ref_id,
    )
    return DocumentAgentToolContext(
        source_ref_id=source_ref_id,
        document_payload=payload,
        document_summary=summary,
    )


def build_runtime(
    *,
    llm_gateway: DocumentLlmPort,
    runtime_store: BaseStore | None,
    tool_context: DocumentAgentToolContext,
) -> AgentRuntime:
    """Create the agent runtime used after document prep completes."""
    return AgentRuntime(
        llm_gateway=llm_gateway,
        tools=DOCUMENT_AGENT_TOOLS,
        tool_context=tool_context,
        runtime_store=runtime_store,
        system_prompt=get_document_agent_system_prompt(),
    )


def build_payload(
    *,
    artifact_repository: ArtifactRepository,
    source_ref_id: str,
) -> DocumentPayload:
    """Load the prepared document payload for one source artifact."""
    return document_chat.build_payload(
        artifact_repository,
        source_ref_id=source_ref_id,
    )


def summarize_ref(
    *,
    artifact_repository: ArtifactRepository,
    source_ref_id: str,
) -> str:
    """Render a deterministic summary for a prepared source artifact."""
    return document_chat.summarize_ref(
        artifact_repository,
        source_ref_id=source_ref_id,
    )


def answer_question_about_ref(
    *,
    artifact_repository: ArtifactRepository,
    source_ref_id: str,
    question: str,
    llm_gateway: DocumentLlmPort | None,
) -> str:
    """Answer a document question using a prepared source artifact."""
    return document_chat.answer_question_about_ref(
        artifact_repository,
        source_ref_id=source_ref_id,
        question=question,
        llm_gateway=llm_gateway,
    )


def build_context_by_ref(
    *,
    artifact_repository: ArtifactRepository,
    source_ref_id: str,
) -> str:
    """Build chat context text from a prepared source artifact."""
    return document_chat.build_context_by_ref(
        artifact_repository,
        source_ref_id=source_ref_id,
    )
