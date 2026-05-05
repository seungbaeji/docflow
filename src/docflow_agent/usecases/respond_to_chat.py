from __future__ import annotations

from collections.abc import Callable

from langgraph.store.base import BaseStore

from docflow_agent.config.prompt import get_chat_system_prompt
from docflow_agent.errors import DocumentAgentRuntimeError
from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.ports.chat_history import ChatHistoryPort
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.ports.session_context import SessionDocumentStore
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument
from docflow_agent.usecases.chat import respond_in_chat
from docflow_agent.workflow.chat.factory import (
    answer_question_about_ref,
    build_context_by_ref,
    build_runtime,
    prepare_context,
)


def respond_to_chat(
    *,
    artifact_repository: ArtifactRepository,
    llm_gateway: DocumentLlmPort,
    chat_history_store: ChatHistoryPort,
    runtime_store: BaseStore | None,
    session_document_store: SessionDocumentStore,
    workflow_run_store: WorkflowRunStore,
    vector_store: VectorStorePort,
    pdf_client: OpenDataLoaderPdfClient | None,
    pdf_parser: Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument],
    session_id: str,
    message: str,
) -> str:
    current_source_ref = session_document_store.get_current_source_ref(session_id)
    current_upload_id = session_document_store.get_current_upload_id(session_id)

    if (current_source_ref is not None or current_upload_id is not None) and _requires_document_agent(
        message
    ):
        tool_context = prepare_context(
            artifact_repository=artifact_repository,
            session_document_store=session_document_store,
            workflow_run_store=workflow_run_store,
            vector_store=vector_store,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
            session_id=session_id,
            message=message,
        )
        runtime = build_runtime(
            llm_gateway=llm_gateway,
            runtime_store=runtime_store,
            tool_context=tool_context,
        )
        try:
            return runtime.run(prompt=message).answer
        except DocumentAgentRuntimeError:
            if _requires_document_processing(message):
                return tool_context.document_summary
            return answer_question_about_ref(
                artifact_repository=artifact_repository,
                source_ref_id=tool_context.source_ref_id,
                question=message,
                llm_gateway=llm_gateway,
                pdf_client=pdf_client,
                pdf_parser=pdf_parser,
            )

    document_context = None
    if current_source_ref is not None:
        document_context = build_context_by_ref(
            artifact_repository=artifact_repository,
            source_ref_id=current_source_ref,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )
    return respond_in_chat(
        message=message,
        session_id=session_id,
        llm_gateway=llm_gateway,
        chat_history_store=chat_history_store,
        system_prompt=get_chat_system_prompt(),
        document_context=document_context,
    )


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(keyword in lowered for keyword in keywords)


def _requires_document_processing(message: str) -> bool:
    return _contains_any(
        message,
        (
            "분석",
            "읽어",
            "읽고",
            "해당 문서",
            "이 문서",
            "pdf",
            "문서",
            "analyze",
            "read",
            "document",
        ),
    )


def _requires_document_question(message: str) -> bool:
    return _contains_any(
        message,
        (
            "전체",
            "내용",
            "상세",
            "자세히",
            "무슨",
            "무엇",
            "금액",
            "이름",
            "요약",
            "설명",
            "해당 문서",
            "이 문서",
            "full",
            "detail",
            "content",
            "summary",
            "question",
        ),
    )


def _requires_document_agent(message: str) -> bool:
    return _requires_document_processing(message) or _requires_document_question(message)
