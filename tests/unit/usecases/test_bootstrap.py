from docflow_agent.bootstrap import build_container
from docflow_agent.config.settings import ApiSettings, AppSettings, LlmSettings, Settings
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.outbound.testing.queue import InMemoryWorkflowQueue
from docflow_agent.outbound.testing.rdbms import InMemoryProcessingRecordStore
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.outbound.testing.vector_store import InMemoryVectorStore


def _settings_without_env() -> Settings:
    return Settings.model_construct(
        app=AppSettings(),
        api=ApiSettings(),
        llm=LlmSettings(),
    )


def test_build_container_wires_testing_dependencies_by_default() -> None:
    container = build_container(settings=_settings_without_env())

    assert isinstance(container.artifact_repository, InMemoryArtifactRepository)
    assert isinstance(container.llm_gateway, StubDocumentLlmGateway)
    assert isinstance(container.processing_record_store, InMemoryProcessingRecordStore)
    assert isinstance(container.vector_store, InMemoryVectorStore)
    assert isinstance(container.workflow_queue, InMemoryWorkflowQueue)
    assert container.document_usecases.artifact_repository is container.artifact_repository
    assert container.document_workflow is not None


def test_build_container_uses_injected_dependencies() -> None:
    repository = InMemoryArtifactRepository()
    processing_store = InMemoryProcessingRecordStore()
    vector_store = InMemoryVectorStore()
    queue = InMemoryWorkflowQueue()
    llm_gateway = StubDocumentLlmGateway(summary_response="Injected summary")

    container = build_container(
        settings=_settings_without_env(),
        artifact_repository=repository,
        llm_gateway=llm_gateway,
        processing_record_store=processing_store,
        vector_store=vector_store,
        workflow_queue=queue,
    )

    assert container.artifact_repository is repository
    assert container.llm_gateway is llm_gateway
    assert container.processing_record_store is processing_store
    assert container.vector_store is vector_store
    assert container.workflow_queue is queue
    assert container.workflow_runtime.workflow_queue is queue
