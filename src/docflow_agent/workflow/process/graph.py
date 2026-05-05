from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from docflow_agent.types.value.results import UsecaseOutcome
from docflow_agent.types.value.workflow import HumanDecision
from docflow_agent.workflow.nodes import (
    WorkflowRuntime,
    analyze_node,
    categorize_units_node,
    combine_bundle_node,
    compose_mail_node,
    filter_dataset_node,
    load_source_node,
    parse_units_node,
    reject_send_mail_node,
    request_send_mail_approval_node,
    select_flow_node,
    send_mail_node,
    unknown_node,
)
from docflow_agent.workflow.process.routing import route_mail_approval, route_selected_flow
from docflow_agent.workflow.state import WorkflowState


def build_workflow(
    *,
    load_source: Callable[[str], str],
    parse_units: Callable[[str], list[str]],
    categorize_units: Callable[[list[str]], list[str]],
    combine_bundle: Callable[[list[str]], str],
    analyze: Callable[[str], UsecaseOutcome],
    filter_dataset: Callable[[str], str],
    compose_mail: Callable[[str], str],
    send_mail: Callable[[str], UsecaseOutcome],
    reject_send_mail: Callable[[str | None], UsecaseOutcome],
    handle_unknown: Callable[[str], UsecaseOutcome],
    workflow_runtime: WorkflowRuntime | None = None,
) -> Any:
    active_workflow_runtime = workflow_runtime or WorkflowRuntime()
    graph = StateGraph(WorkflowState)
    graph.add_node("select_flow", select_flow_node)
    graph.add_node("load_source", partial(load_source_node, load_source=load_source))
    graph.add_node("parse_units", partial(parse_units_node, parse_units=parse_units))
    graph.add_node("categorize_units", partial(categorize_units_node, categorize_units=categorize_units))
    graph.add_node("combine_bundle", partial(combine_bundle_node, combine_bundle=combine_bundle))
    graph.add_node("analyze", partial(analyze_node, analyze=analyze))
    graph.add_node("filter_dataset", partial(filter_dataset_node, filter_dataset=filter_dataset))
    graph.add_node("compose_mail", partial(compose_mail_node, compose_mail=compose_mail))
    graph.add_node(
        "request_send_mail_approval",
        partial(request_send_mail_approval_node, workflow_runtime=active_workflow_runtime),
    )
    graph.add_node(
        "send_mail",
        partial(send_mail_node, send_mail=send_mail, workflow_runtime=active_workflow_runtime),
    )
    graph.add_node(
        "reject_send_mail",
        partial(
            reject_send_mail_node,
            reject_send_mail=reject_send_mail,
            workflow_runtime=active_workflow_runtime,
        ),
    )
    graph.add_node("unknown", partial(unknown_node, handle_unknown=handle_unknown))

    graph.add_edge(START, "select_flow")
    graph.add_conditional_edges(
        "select_flow",
        route_selected_flow,
        {
            "document_process": "load_source",
            "document_to_mail": "load_source",
            "unknown": "unknown",
        },
    )
    graph.add_edge("load_source", "parse_units")
    graph.add_edge("parse_units", "categorize_units")
    graph.add_edge("categorize_units", "combine_bundle")
    graph.add_conditional_edges(
        "combine_bundle",
        route_selected_flow,
        {
            "document_process": "analyze",
            "document_to_mail": "filter_dataset",
            "unknown": "unknown",
        },
    )
    graph.add_edge("analyze", END)
    graph.add_edge("filter_dataset", "compose_mail")
    graph.add_edge("compose_mail", "request_send_mail_approval")
    graph.add_conditional_edges(
        "request_send_mail_approval",
        route_mail_approval,
        {
            "awaiting_approval": END,
            "approved": "send_mail",
            "rejected": "reject_send_mail",
        },
    )
    graph.add_edge("send_mail", END)
    graph.add_edge("reject_send_mail", END)
    graph.add_edge("unknown", END)
    return graph.compile()


def invoke_workflow(
    user_input: str,
    workflow: Any,
    human_decisions: list[HumanDecision] | None = None,
) -> WorkflowState:
    initial_state: WorkflowState = {"user_input": user_input}
    if human_decisions:
        initial_state["human_decisions"] = human_decisions
    return cast(WorkflowState, workflow.invoke(initial_state))


def state_to_response(state: WorkflowState) -> dict[str, object]:
    response: dict[str, object] = {
        "flow": state.get("flow", "unknown"),
        "current_step": state.get("current_step", ""),
        "result": state.get("result"),
        "error": state.get("error"),
        "source_refs": state.get("source_refs", []),
        "unit_refs": state.get("unit_refs", []),
        "categorized_unit_refs": state.get("categorized_unit_refs", []),
        "bundle_refs": state.get("bundle_refs", []),
        "dataset_refs": state.get("dataset_refs", []),
        "output_refs": state.get("output_refs", []),
    }
    if "pending_human_decision" in state:
        response["pending_human_decision"] = state["pending_human_decision"]
    return response
