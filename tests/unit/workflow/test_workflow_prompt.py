from docflow_agent.workflow.document_workflow import (
    create_document_workflow,
    invoke_document_workflow,
    workflow_state_to_response,
)
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
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


def test_workflow_facade_accepts_human_decisions_and_serializes_state() -> None:
    repository = InMemoryArtifactRepository()
    workflow = create_document_workflow(
        usecases=RepositoryBackedDocumentUsecases(repository),
        artifact_repository=repository,
    )

    state = invoke_document_workflow(
        user_input="엑셀에서 미정산 건을 찾아 메일로 보내줘",
        human_decisions=[
            {
                "decision_id": "approve_send_mail",
                "kind": "approve",
                "message": "Approve sending the generated mail draft?",
                "options": ["approve", "reject"],
                "selected": "approve",
                "payload": None,
            }
        ],
        workflow=workflow,
    )

    response = workflow_state_to_response(state)

    assert response["flow"] == "document_to_mail"
    assert response["current_step"] == "send_mail"
    assert response["result"] == "Mail sent after approval."
    assert response["output_refs"]
