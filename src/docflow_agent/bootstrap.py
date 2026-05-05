from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from docflow_agent.outbound.external.llm import ExternalDocumentLlmGateway, build_llm_client
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.outbound.testing.queue import InMemoryWorkflowQueue
from docflow_agent.outbound.testing.rdbms import InMemoryProcessingRecordStore
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.outbound.testing.vector_store import InMemoryVectorStore
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.queue import WorkflowQueuePort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import ProcessingRecordPort
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.settings import Settings, get_settings
from docflow_agent.usecases.document_workflow import RepositoryBackedDocumentUsecases
from docflow_agent.workflow.document_workflow import create_document_workflow
from docflow_agent.workflow.nodes import WorkflowRuntime


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    artifact_repository: ArtifactRepository
    llm_gateway: DocumentLlmPort
    processing_record_store: ProcessingRecordPort
    vector_store: VectorStorePort
    workflow_queue: WorkflowQueuePort
    document_usecases: RepositoryBackedDocumentUsecases
    workflow_runtime: WorkflowRuntime
    document_workflow: Any


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
    processing_record_store: ProcessingRecordPort | None = None,
    vector_store: VectorStorePort | None = None,
    workflow_queue: WorkflowQueuePort | None = None,
) -> AppContainer:
    active_settings = settings or get_settings()
    active_repository = artifact_repository or InMemoryArtifactRepository()
    active_llm_gateway = llm_gateway or _build_llm_gateway(active_settings)
    active_processing_record_store = processing_record_store or InMemoryProcessingRecordStore()
    active_vector_store = vector_store or InMemoryVectorStore()
    active_workflow_queue = workflow_queue or InMemoryWorkflowQueue()

    document_usecases = RepositoryBackedDocumentUsecases(
        artifact_repository=active_repository,
        llm_gateway=active_llm_gateway,
        processing_record_store=active_processing_record_store,
        vector_store=active_vector_store,
    )
    workflow_runtime = WorkflowRuntime(
        processing_record_store=active_processing_record_store,
        workflow_queue=active_workflow_queue,
    )
    document_workflow = create_document_workflow(
        usecases=document_usecases,
        artifact_repository=active_repository,
        workflow_runtime=workflow_runtime,
    )

    return AppContainer(
        settings=active_settings,
        artifact_repository=active_repository,
        llm_gateway=active_llm_gateway,
        processing_record_store=active_processing_record_store,
        vector_store=active_vector_store,
        workflow_queue=active_workflow_queue,
        document_usecases=document_usecases,
        workflow_runtime=workflow_runtime,
        document_workflow=document_workflow,
    )


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    return build_container()
