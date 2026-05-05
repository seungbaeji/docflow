from __future__ import annotations

from docflow_agent.workflow.document import DocumentWorkflowServices
from docflow_agent.workflow.routes import route_flow
from docflow_agent.workflow.state import WorkflowState
from docflow_agent.workflow.nodes.shared import append_artifact_ref, artifact_ref


def select_flow_node(state: WorkflowState) -> WorkflowState:
    state["flow"] = route_flow(state)
    state["current_step"] = "select_flow"
    return state


def load_source_node(state: WorkflowState, usecases: DocumentWorkflowServices) -> WorkflowState:
    source_ref_id = usecases["load_source"](state["user_input"])
    source_ref = artifact_ref("source", source_ref_id)
    append_artifact_ref(state, "source_refs", source_ref)
    state["selected_source_ref"] = source_ref
    state["current_step"] = "load_source"
    return state


def parse_units_node(state: WorkflowState, usecases: DocumentWorkflowServices) -> WorkflowState:
    source_ref_id = state["selected_source_ref"]["ref_id"]
    unit_refs = [artifact_ref("unit", ref_id) for ref_id in usecases["parse_units"](source_ref_id)]
    for unit_ref in unit_refs:
        append_artifact_ref(state, "unit_refs", unit_ref)
    if unit_refs:
        state["selected_unit_ref"] = unit_refs[-1]
    state["current_step"] = "parse_units"
    return state


def categorize_units_node(state: WorkflowState, usecases: DocumentWorkflowServices) -> WorkflowState:
    parsed_unit_refs = [ref["ref_id"] for ref in state.get("unit_refs", []) if ref["kind"] == "unit"]
    categorized_unit_refs = [
        artifact_ref("unit", ref_id) for ref_id in usecases["categorize_units"](parsed_unit_refs)
    ]
    state["categorized_unit_refs"] = categorized_unit_refs
    if categorized_unit_refs:
        state["selected_unit_ref"] = categorized_unit_refs[-1]
    state["current_step"] = "categorize_units"
    return state


def combine_bundle_node(state: WorkflowState, usecases: DocumentWorkflowServices) -> WorkflowState:
    categorized_unit_ref_ids = [ref["ref_id"] for ref in state.get("categorized_unit_refs", [])]
    bundle_ref = artifact_ref("bundle", usecases["combine_bundle"](categorized_unit_ref_ids))
    append_artifact_ref(state, "bundle_refs", bundle_ref)
    state["selected_bundle_ref"] = bundle_ref
    state["current_step"] = "combine_bundle"
    return state


def analyze_node(state: WorkflowState, usecases: DocumentWorkflowServices) -> WorkflowState:
    bundle_ref_id = state["selected_bundle_ref"]["ref_id"]
    outcome = usecases["analyze"](bundle_ref_id)
    analysis_ref = artifact_ref("analysis", outcome.ref_id)
    append_artifact_ref(state, "output_refs", analysis_ref)
    state["result"] = outcome.message
    state["current_step"] = "analyze"
    return state


def unknown_node(state: WorkflowState, usecases: DocumentWorkflowServices) -> WorkflowState:
    outcome = usecases["handle_unknown"](state["user_input"])
    result_ref = artifact_ref("result", outcome.ref_id)
    append_artifact_ref(state, "output_refs", result_ref)
    state["error"] = outcome.message
    state["current_step"] = "unknown"
    return state
