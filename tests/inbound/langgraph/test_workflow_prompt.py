from docflow_agent.inbound.langgraph.workflow import create_document_workflow
from docflow_agent.outbound.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.usecases.document_workflow import RepositoryBackedDocumentUsecases


def test_prompt_routes_to_document_process_and_creates_artifact_refs() -> None:
    repository = InMemoryArtifactRepository()
    workflow = create_document_workflow(
        usecases=RepositoryBackedDocumentUsecases(repository),
        artifact_repository=repository,
    )

    state = workflow.invoke({"user_input": "엑셀 문서를 분석해줘"})

    assert state["flow"] == "document_process"
    assert state["source_refs"]
    assert state["unit_refs"]
    assert state["bundle_refs"]
    assert state["output_refs"]
    assert state["output_refs"][-1]["kind"] == "analysis"
    assert state["result"]

