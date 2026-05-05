from __future__ import annotations

from docflow_agent.workflow.document import DocumentWorkflowServices
from docflow_agent.workflow.nodes.runtime import (
    WorkflowRuntime,
    enqueue_workflow_message,
    save_workflow_run,
)
from docflow_agent.workflow.nodes.shared import append_artifact_ref, artifact_ref
from docflow_agent.workflow.routes import get_human_decision
from docflow_agent.workflow.state import WorkflowState


def filter_dataset_node(state: WorkflowState, usecases: DocumentWorkflowServices) -> WorkflowState:
    bundle_ref_id = state["selected_bundle_ref"]["ref_id"]
    dataset_ref = artifact_ref("dataset", usecases["filter_dataset"](bundle_ref_id))
    append_artifact_ref(state, "dataset_refs", dataset_ref)
    state["current_step"] = "filter_dataset"
    return state


def compose_mail_node(state: WorkflowState, usecases: DocumentWorkflowServices) -> WorkflowState:
    dataset_ref_id = state["dataset_refs"][-1]["ref_id"]
    draft_ref = artifact_ref("draft", usecases["compose_mail"](dataset_ref_id))
    append_artifact_ref(state, "output_refs", draft_ref)
    state["current_step"] = "compose_mail"
    return state


def request_send_mail_approval_node(
    state: WorkflowState,
    usecases: DocumentWorkflowServices,
    workflow_runtime: WorkflowRuntime,
) -> WorkflowState:
    del usecases
    decision = get_human_decision(state, "approve_send_mail")
    state["current_step"] = "request_send_mail_approval"
    draft_ref_id = state["output_refs"][-1]["ref_id"]
    if decision is None:
        state["pending_human_decision"] = {
            "decision_id": "approve_send_mail",
            "kind": "approve",
            "message": "Approve sending the generated mail draft?",
            "options": ["approve", "reject"],
            "selected": None,
            "payload": {"draft_ref_id": draft_ref_id},
        }
        save_workflow_run(
            workflow_runtime,
            record_id=f"workflow-pending-{draft_ref_id}",
            status="pending_approval",
            artifact_refs=[draft_ref_id],
            metadata={"decision_id": "approve_send_mail", "step": "request_send_mail_approval"},
        )
        enqueue_workflow_message(
            workflow_runtime,
            message_id=f"approval-request-{draft_ref_id}",
            topic="workflow.approval_requested",
            payload={"draft_ref_id": draft_ref_id, "decision_id": "approve_send_mail"},
            metadata={"step": "request_send_mail_approval"},
        )
        state["result"] = "Awaiting approval to send mail."
        return state

    state.pop("pending_human_decision", None)
    if decision["selected"] is not None:
        save_workflow_run(
            workflow_runtime,
            record_id=f"workflow-decision-{draft_ref_id}",
            status=f"decision_{decision['selected']}",
            artifact_refs=[draft_ref_id],
            metadata={"decision_id": decision["decision_id"], "selected": decision["selected"]},
        )
    return state


def send_mail_node(
    state: WorkflowState,
    usecases: DocumentWorkflowServices,
    workflow_runtime: WorkflowRuntime,
) -> WorkflowState:
    draft_ref_id = state["output_refs"][-1]["ref_id"]
    outcome = usecases["send_mail"](draft_ref_id)
    result_ref = artifact_ref("result", outcome.ref_id)
    append_artifact_ref(state, "output_refs", result_ref)
    enqueue_workflow_message(
        workflow_runtime,
        message_id=f"workflow-send-{outcome.ref_id}",
        topic="workflow.mail_sent",
        payload={"draft_ref_id": draft_ref_id, "result_ref_id": outcome.ref_id},
        metadata={"step": "send_mail"},
    )
    state["result"] = outcome.message
    state["current_step"] = "send_mail"
    return state


def reject_send_mail_node(
    state: WorkflowState,
    usecases: DocumentWorkflowServices,
    workflow_runtime: WorkflowRuntime,
) -> WorkflowState:
    draft_ref_id = state.get("output_refs", [])[-1]["ref_id"] if state.get("output_refs") else None
    outcome = usecases["reject_send_mail"](draft_ref_id)
    result_ref = artifact_ref("result", outcome.ref_id)
    append_artifact_ref(state, "output_refs", result_ref)
    enqueue_workflow_message(
        workflow_runtime,
        message_id=f"workflow-reject-{outcome.ref_id}",
        topic="workflow.mail_rejected",
        payload={"draft_ref_id": draft_ref_id, "result_ref_id": outcome.ref_id},
        metadata={"step": "reject_send_mail"},
    )
    state.pop("pending_human_decision", None)
    state["result"] = outcome.message
    state["current_step"] = "reject_send_mail"
    return state
