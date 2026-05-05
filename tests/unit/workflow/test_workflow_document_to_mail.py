from docflow_agent.workflow.nodes import WorkflowRuntime
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.outbound.testing.queue import InMemoryWorkflowQueue
from docflow_agent.outbound.testing.rdbms import InMemoryWorkflowRunStore
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.outbound.testing.vector_store import InMemoryVectorStore
from docflow_agent.workflow.process import build_workflow
from support.document_workflow import build_document_workflow_kwargs


def test_document_to_mail_stops_for_pending_approval() -> None:
    repository = InMemoryArtifactRepository()
    workflow = build_workflow(**build_document_workflow_kwargs(artifact_repository=repository))

    state = workflow.invoke({"user_input": "엑셀에서 미정산 건을 찾아 메일로 보내줘"})

    assert state["flow"] == "document_to_mail"
    assert state["pending_human_decision"]["decision_id"] == "approve_send_mail"
    assert state["pending_human_decision"]["selected"] is None
    assert all(ref["kind"] != "result" for ref in state["output_refs"])
    assert state["current_step"] == "request_send_mail_approval"


def test_document_to_mail_sends_mail_after_approval() -> None:
    repository = InMemoryArtifactRepository()
    workflow = build_workflow(**build_document_workflow_kwargs(artifact_repository=repository))

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
    workflow = build_workflow(**build_document_workflow_kwargs(artifact_repository=repository))

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
    workflow_run_store = InMemoryWorkflowRunStore()
    queue = InMemoryWorkflowQueue()
    workflow = build_workflow(
        workflow_runtime=WorkflowRuntime(
            workflow_run_store=workflow_run_store,
            workflow_queue=queue,
        ),
        **build_document_workflow_kwargs(
            artifact_repository=repository,
            llm_gateway=StubDocumentLlmGateway(summary_response="Workflow-generated mail body"),
            workflow_run_store=workflow_run_store,
            vector_store=InMemoryVectorStore(),
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
    assert workflow_run_store.load_workflow_run(result_ref_id).status == "sent"
    queued = queue.dequeue()
    assert queued is not None
    assert queued.topic == "workflow.mail_sent"


def test_document_to_mail_workflow_records_pending_approval_and_enqueues_request() -> None:
    repository = InMemoryArtifactRepository()
    workflow_run_store = InMemoryWorkflowRunStore()
    queue = InMemoryWorkflowQueue()
    workflow = build_workflow(
        workflow_runtime=WorkflowRuntime(
            workflow_run_store=workflow_run_store,
            workflow_queue=queue,
        ),
        **build_document_workflow_kwargs(
            artifact_repository=repository,
            workflow_run_store=workflow_run_store,
            vector_store=InMemoryVectorStore(),
        ),
    )

    state = workflow.invoke({"user_input": "엑셀에서 미정산 건을 찾아 메일로 보내줘"})

    draft_ref_id = next(ref["ref_id"] for ref in state["output_refs"] if ref["kind"] == "draft")
    record = workflow_run_store.load_workflow_run(f"workflow-pending-{draft_ref_id}")
    assert record.status == "pending_approval"
    queued = queue.dequeue()
    assert queued is not None
    assert queued.topic == "workflow.approval_requested"
    assert queued.payload["draft_ref_id"] == draft_ref_id
