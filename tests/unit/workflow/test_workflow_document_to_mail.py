from docflow_agent.workflow.document_workflow import create_document_workflow
from docflow_agent.workflow.nodes import WorkflowRuntime
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.outbound.testing.queue import InMemoryWorkflowQueue
from docflow_agent.outbound.testing.rdbms import InMemoryProcessingRecordStore
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.outbound.testing.vector_store import InMemoryVectorStore
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


def test_document_to_mail_workflow_uses_port_backed_usecase_dependencies() -> None:
    repository = InMemoryArtifactRepository()
    processing_store = InMemoryProcessingRecordStore()
    queue = InMemoryWorkflowQueue()
    usecases = RepositoryBackedDocumentUsecases(
        artifact_repository=repository,
        llm_gateway=StubDocumentLlmGateway(summary_response="Workflow-generated mail body"),
        processing_record_store=processing_store,
        vector_store=InMemoryVectorStore(),
    )
    workflow = create_document_workflow(
        usecases=usecases,
        artifact_repository=repository,
        workflow_runtime=WorkflowRuntime(
            processing_record_store=processing_store,
            workflow_queue=queue,
        ),
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

    draft_ref_id = next(ref["ref_id"] for ref in state["output_refs"] if ref["kind"] == "draft")
    draft = repository.load("draft", draft_ref_id)
    assert draft["body"] == "Workflow-generated mail body"
    result_ref_id = state["output_refs"][-1]["ref_id"]
    assert processing_store.load_processing_record(result_ref_id).status == "sent"
    queued = queue.dequeue()
    assert queued is not None
    assert queued.topic == "workflow.mail_sent"


def test_document_to_mail_workflow_records_pending_approval_and_enqueues_request() -> None:
    repository = InMemoryArtifactRepository()
    processing_store = InMemoryProcessingRecordStore()
    queue = InMemoryWorkflowQueue()
    workflow = create_document_workflow(
        artifact_repository=repository,
        workflow_runtime=WorkflowRuntime(
            processing_record_store=processing_store,
            workflow_queue=queue,
        ),
    )

    state = workflow.invoke({"user_input": "엑셀에서 미정산 건을 찾아 메일로 보내줘"})

    draft_ref_id = next(ref["ref_id"] for ref in state["output_refs"] if ref["kind"] == "draft")
    record = processing_store.load_processing_record(f"workflow-pending-{draft_ref_id}")
    assert record.status == "pending_approval"
    queued = queue.dequeue()
    assert queued is not None
    assert queued.topic == "workflow.approval_requested"
    assert queued.payload["draft_ref_id"] == draft_ref_id
