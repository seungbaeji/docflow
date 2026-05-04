from __future__ import annotations

from typing import Literal, Protocol

from docflow_agent.inbound.langgraph.routes import get_human_decision, route_flow
from docflow_agent.inbound.langgraph.state import ArtifactKind, ArtifactRef, WorkflowState
from docflow_agent.usecases.document_workflow import UsecaseOutcome


class DocumentWorkflowUsecases(Protocol):
    def load_source(self, user_input: str) -> str:
        ...

    def parse_units(self, source_ref_id: str) -> list[str]:
        ...

    def categorize_units(self, unit_ref_ids: list[str]) -> list[str]:
        ...

    def combine_bundle(self, unit_ref_ids: list[str]) -> str:
        ...

    def analyze(self, bundle_ref_id: str) -> UsecaseOutcome:
        ...

    def filter_dataset(self, bundle_ref_id: str) -> str:
        ...

    def compose_mail(self, dataset_ref_id: str) -> str:
        ...

    def send_mail(self, draft_ref_id: str) -> UsecaseOutcome:
        ...

    def reject_send_mail(self, draft_ref_id: str | None) -> UsecaseOutcome:
        ...

    def handle_unknown(self, user_input: str) -> UsecaseOutcome:
        ...


ArtifactRefListKey = Literal["source_refs", "unit_refs", "bundle_refs", "dataset_refs", "output_refs"]


def _artifact_ref(kind: ArtifactKind, ref_id: str) -> ArtifactRef:
    return {"kind": kind, "ref_id": ref_id}


def _append_artifact_ref(state: WorkflowState, key: ArtifactRefListKey, ref: ArtifactRef) -> None:
    refs = list(state.get(key, []))
    refs.append(ref)
    state[key] = refs


def select_flow_node(state: WorkflowState) -> WorkflowState:
    state["flow"] = route_flow(state)
    state["current_step"] = "select_flow"
    return state


def load_source_node(state: WorkflowState, usecases: DocumentWorkflowUsecases) -> WorkflowState:
    source_ref_id = usecases.load_source(state["user_input"])
    source_ref = _artifact_ref("source", source_ref_id)
    _append_artifact_ref(state, "source_refs", source_ref)
    state["selected_source_ref"] = source_ref
    state["current_step"] = "load_source"
    return state


def parse_units_node(state: WorkflowState, usecases: DocumentWorkflowUsecases) -> WorkflowState:
    source_ref_id = state["selected_source_ref"]["ref_id"]
    unit_refs = [_artifact_ref("unit", ref_id) for ref_id in usecases.parse_units(source_ref_id)]
    for unit_ref in unit_refs:
        _append_artifact_ref(state, "unit_refs", unit_ref)
    if unit_refs:
        state["selected_unit_ref"] = unit_refs[-1]
    state["current_step"] = "parse_units"
    return state


def categorize_units_node(state: WorkflowState, usecases: DocumentWorkflowUsecases) -> WorkflowState:
    parsed_unit_refs = [
        ref["ref_id"] for ref in state.get("unit_refs", []) if ref["kind"] == "unit"
    ]
    categorized_unit_refs = [
        _artifact_ref("unit", ref_id) for ref_id in usecases.categorize_units(parsed_unit_refs)
    ]
    for unit_ref in categorized_unit_refs:
        _append_artifact_ref(state, "unit_refs", unit_ref)
    if categorized_unit_refs:
        state["selected_unit_ref"] = categorized_unit_refs[-1]
    state["current_step"] = "categorize_units"
    return state


def combine_bundle_node(state: WorkflowState, usecases: DocumentWorkflowUsecases) -> WorkflowState:
    categorized_unit_ref_ids = [
        ref["ref_id"] for ref in state.get("unit_refs", [])[-2:] if ref["kind"] == "unit"
    ]
    bundle_ref = _artifact_ref("bundle", usecases.combine_bundle(categorized_unit_ref_ids))
    _append_artifact_ref(state, "bundle_refs", bundle_ref)
    state["selected_bundle_ref"] = bundle_ref
    state["current_step"] = "combine_bundle"
    return state


def analyze_node(state: WorkflowState, usecases: DocumentWorkflowUsecases) -> WorkflowState:
    bundle_ref_id = state["selected_bundle_ref"]["ref_id"]
    outcome = usecases.analyze(bundle_ref_id)
    analysis_ref = _artifact_ref("analysis", outcome.ref_id)
    _append_artifact_ref(state, "output_refs", analysis_ref)
    state["result"] = outcome.message
    state["current_step"] = "analyze"
    return state


def filter_dataset_node(state: WorkflowState, usecases: DocumentWorkflowUsecases) -> WorkflowState:
    bundle_ref_id = state["selected_bundle_ref"]["ref_id"]
    dataset_ref = _artifact_ref("dataset", usecases.filter_dataset(bundle_ref_id))
    _append_artifact_ref(state, "dataset_refs", dataset_ref)
    state["current_step"] = "filter_dataset"
    return state


def compose_mail_node(state: WorkflowState, usecases: DocumentWorkflowUsecases) -> WorkflowState:
    dataset_ref_id = state["dataset_refs"][-1]["ref_id"]
    draft_ref = _artifact_ref("draft", usecases.compose_mail(dataset_ref_id))
    _append_artifact_ref(state, "output_refs", draft_ref)
    state["current_step"] = "compose_mail"
    return state


def request_send_mail_approval_node(
    state: WorkflowState,
    usecases: DocumentWorkflowUsecases,
) -> WorkflowState:
    del usecases
    decision = get_human_decision(state, "approve_send_mail")
    state["current_step"] = "request_send_mail_approval"
    if decision is None:
        state["pending_human_decision"] = {
            "decision_id": "approve_send_mail",
            "kind": "approve",
            "message": "Approve sending the generated mail draft?",
            "options": ["approve", "reject"],
            "selected": None,
            "payload": {"draft_ref_id": state["output_refs"][-1]["ref_id"]},
        }
        state["result"] = "Awaiting approval to send mail."
        return state

    state.pop("pending_human_decision", None)
    return state


def send_mail_node(state: WorkflowState, usecases: DocumentWorkflowUsecases) -> WorkflowState:
    draft_ref_id = state["output_refs"][-1]["ref_id"]
    outcome = usecases.send_mail(draft_ref_id)
    result_ref = _artifact_ref("result", outcome.ref_id)
    _append_artifact_ref(state, "output_refs", result_ref)
    state["result"] = outcome.message
    state["current_step"] = "send_mail"
    return state


def reject_send_mail_node(state: WorkflowState, usecases: DocumentWorkflowUsecases) -> WorkflowState:
    draft_ref_id = state.get("output_refs", [])[-1]["ref_id"] if state.get("output_refs") else None
    outcome = usecases.reject_send_mail(draft_ref_id)
    result_ref = _artifact_ref("result", outcome.ref_id)
    _append_artifact_ref(state, "output_refs", result_ref)
    state.pop("pending_human_decision", None)
    state["result"] = outcome.message
    state["current_step"] = "reject_send_mail"
    return state


def unknown_node(state: WorkflowState, usecases: DocumentWorkflowUsecases) -> WorkflowState:
    outcome = usecases.handle_unknown(state["user_input"])
    result_ref = _artifact_ref("result", outcome.ref_id)
    _append_artifact_ref(state, "output_refs", result_ref)
    state["error"] = outcome.message
    state["current_step"] = "unknown"
    return state
