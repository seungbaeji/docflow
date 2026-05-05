from __future__ import annotations

from functools import lru_cache
from typing import Callable

from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from docflow_agent.config.settings import Settings, get_settings
from docflow_agent.outbound.external.llm import ExternalDocumentLlmGateway, build_llm_client
from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient, extract_pdf_document
from docflow_agent.outbound.testing.chat_history import InMemoryChatHistoryStore
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.outbound.testing.queue import InMemoryWorkflowQueue
from docflow_agent.outbound.testing.rdbms import InMemoryWorkflowRunStore
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.outbound.testing.session_context import StoreBackedSessionDocumentStore
from docflow_agent.outbound.testing.vector_store import InMemoryVectorStore
from docflow_agent.ports.chat_history import ChatHistoryPort
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.queue import WorkflowQueuePort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.ports.session_context import SessionDocumentStore
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument


class AppContainer:
    def __init__(
        self,
        *,
        settings: Settings,
        artifact_repository: ArtifactRepository,
        llm_gateway: DocumentLlmPort,
        pdf_client: OpenDataLoaderPdfClient,
        pdf_parser: Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument],
        chat_history_store: ChatHistoryPort,
        runtime_store: BaseStore,
        session_document_store: SessionDocumentStore,
        workflow_run_store: WorkflowRunStore,
        vector_store: VectorStorePort,
        workflow_queue: WorkflowQueuePort,
    ) -> None:
        self.settings = settings
        self.artifact_repository = artifact_repository
        self.llm_gateway = llm_gateway
        self.pdf_client = pdf_client
        self.pdf_parser = pdf_parser
        self.chat_history_store = chat_history_store
        self.runtime_store = runtime_store
        self.session_document_store = session_document_store
        self.workflow_run_store = workflow_run_store
        self.vector_store = vector_store
        self.workflow_queue = workflow_queue


def _build_llm_gateway(settings: Settings) -> DocumentLlmPort:
    if settings.llm.provider == "stub":
        return StubDocumentLlmGateway(
            summary_response="Stub summary for unsettled items.",
            answer_response="Stub answer for document question.",
        )
    return ExternalDocumentLlmGateway(client=build_llm_client(settings))


def build_container(
    *,
    settings: Settings | None = None,
    artifact_repository: ArtifactRepository | None = None,
    llm_gateway: DocumentLlmPort | None = None,
    pdf_client: OpenDataLoaderPdfClient | None = None,
    pdf_parser: Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument] | None = None,
    chat_history_store: ChatHistoryPort | None = None,
    runtime_store: BaseStore | None = None,
    session_document_store: SessionDocumentStore | None = None,
    workflow_run_store: WorkflowRunStore | None = None,
    vector_store: VectorStorePort | None = None,
    workflow_queue: WorkflowQueuePort | None = None,
) -> AppContainer:
    active_settings = settings or get_settings()
    active_repository = artifact_repository or InMemoryArtifactRepository()
    active_llm_gateway = llm_gateway or _build_llm_gateway(active_settings)
    active_pdf_client = pdf_client or OpenDataLoaderPdfClient()
    active_pdf_parser = pdf_parser or extract_pdf_document
    active_chat_history_store = chat_history_store or InMemoryChatHistoryStore()
    active_runtime_store = runtime_store or InMemoryStore()
    active_session_document_store = session_document_store or StoreBackedSessionDocumentStore(
        store=active_runtime_store
    )
    active_workflow_run_store = workflow_run_store or InMemoryWorkflowRunStore()
    active_vector_store = vector_store or InMemoryVectorStore()
    active_workflow_queue = workflow_queue or InMemoryWorkflowQueue()

    return AppContainer(
        settings=active_settings,
        artifact_repository=active_repository,
        llm_gateway=active_llm_gateway,
        pdf_client=active_pdf_client,
        pdf_parser=active_pdf_parser,
        chat_history_store=active_chat_history_store,
        runtime_store=active_runtime_store,
        session_document_store=active_session_document_store,
        workflow_run_store=active_workflow_run_store,
        vector_store=active_vector_store,
        workflow_queue=active_workflow_queue,
    )


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    return build_container()
