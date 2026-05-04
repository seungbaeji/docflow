from docflow_agent.inbound.langgraph.workflow import create_document_workflow
from docflow_agent.outbound.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.usecases.document_workflow import RepositoryBackedDocumentUsecases


def test_document_to_mail_stops_for_pending_approval() -> None:
    repository = InMemoryArtifactRepository()
    workflow = create_document_workflow(
        usecases=RepositoryBackedDocumentUsecases(repository),
        artifact_repository=repository,
    )

    state = workflow.invoke({"user_input": "엑셀에서 미정산 건을 찾아 메일로 보내줘"})

    assert state["flow"] == "document_to_mail"
    assert state["pending_human_decision"]["decision_id"] == "approve_send_mail"
    assert state["pending_human_decision"]["selected"] is None
    assert all(ref["kind"] != "result" for ref in state["output_refs"])
    assert state["current_step"] == "request_send_mail_approval"


def test_document_to_mail_sends_mail_after_approval() -> None:
    repository = InMemoryArtifactRepository()
    workflow = create_document_workflow(
        usecases=RepositoryBackedDocumentUsecases(repository),
        artifact_repository=repository,
    )

    state = workflow.invoke(
        {
            "user_input": "엑셀에서 미정산 건을 찾아 메일로 보내줘",
            "human_decisions": [
                {
                    "decision_id": "approve_send_mail",
                    "kind": "approve",
                    "message": "Approve sending the generated mail draft?",
                    "options": ["approve", "reject"],
                    "selected": "approve",
                    "payload": None,
                }
            ],
        }
    )

    assert state["current_step"] == "send_mail"
    assert state["result"] == "Mail sent after approval."
    assert state["output_refs"][-1]["kind"] == "result"


def test_document_to_mail_rejects_mail_safely() -> None:
    repository = InMemoryArtifactRepository()
    workflow = create_document_workflow(
        usecases=RepositoryBackedDocumentUsecases(repository),
        artifact_repository=repository,
    )

    state = workflow.invoke(
        {
            "user_input": "엑셀에서 미정산 건을 찾아 메일로 보내줘",
            "human_decisions": [
                {
                    "decision_id": "approve_send_mail",
                    "kind": "approve",
                    "message": "Approve sending the generated mail draft?",
                    "options": ["approve", "reject"],
                    "selected": "reject",
                    "payload": None,
                }
            ],
        }
    )

    assert state["current_step"] == "reject_send_mail"
    assert state["result"] == "User rejected mail sending."
    assert state["output_refs"][-1]["kind"] == "result"

