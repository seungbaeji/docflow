from __future__ import annotations

from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from docflow_agent.inbound.langgraph.nodes import (
    DocumentWorkflowUsecases,
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
from docflow_agent.inbound.langgraph.state import WorkflowState
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.usecases.document_workflow import RepositoryBackedDocumentUsecases


def _route_selected_flow(state: WorkflowState) -> str:
    return state["flow"]


def _route_mail_approval(state: WorkflowState) -> str:
    decision = state.get("pending_human_decision")
    if decision is not None and decision.get("selected") is None:
        return "awaiting_approval"

    selected = next(
        (
            item["selected"]
            for item in state.get("human_decisions", [])
            if item["decision_id"] == "approve_send_mail"
        ),
        None,
    )
    if selected == "approve":
        return "approved"
    return "rejected"


def build_document_workflow(
    usecases: DocumentWorkflowUsecases,
    artifact_repository: ArtifactRepository,
) -> Any:
    del artifact_repository
    graph = StateGraph(WorkflowState)
    graph.add_node("select_flow", select_flow_node)
    graph.add_node("load_source", partial(load_source_node, usecases=usecases))
    graph.add_node("parse_units", partial(parse_units_node, usecases=usecases))
    graph.add_node("categorize_units", partial(categorize_units_node, usecases=usecases))
    graph.add_node("combine_bundle", partial(combine_bundle_node, usecases=usecases))
    graph.add_node("analyze", partial(analyze_node, usecases=usecases))
    graph.add_node("filter_dataset", partial(filter_dataset_node, usecases=usecases))
    graph.add_node("compose_mail", partial(compose_mail_node, usecases=usecases))
    graph.add_node(
        "request_send_mail_approval",
        partial(request_send_mail_approval_node, usecases=usecases),
    )
    graph.add_node("send_mail", partial(send_mail_node, usecases=usecases))
    graph.add_node("reject_send_mail", partial(reject_send_mail_node, usecases=usecases))
    graph.add_node("unknown", partial(unknown_node, usecases=usecases))

    graph.add_edge(START, "select_flow")
    graph.add_conditional_edges(
        "select_flow",
        _route_selected_flow,
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
        _route_selected_flow,
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
        _route_mail_approval,
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


def create_document_workflow(
    usecases: DocumentWorkflowUsecases | None = None,
    artifact_repository: ArtifactRepository | None = None,
) -> Any:
    repository = artifact_repository or InMemoryArtifactRepository()
    workflow_usecases = usecases or RepositoryBackedDocumentUsecases(repository)
    return build_document_workflow(
        usecases=workflow_usecases,
        artifact_repository=repository,
    )
