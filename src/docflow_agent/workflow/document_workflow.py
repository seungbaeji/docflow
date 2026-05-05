from __future__ import annotations

from functools import partial
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.outbound.testing.queue import InMemoryWorkflowQueue
from docflow_agent.outbound.testing.rdbms import InMemoryProcessingRecordStore
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.outbound.testing.vector_store import InMemoryVectorStore
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.usecases.document_workflow import RepositoryBackedDocumentUsecases
from docflow_agent.workflow.nodes import (
    DocumentWorkflowUsecases,
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
from docflow_agent.workflow.state import HumanDecision, WorkflowState


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
    workflow_runtime: WorkflowRuntime | None = None,
) -> Any:
    del artifact_repository
    active_workflow_runtime = workflow_runtime or WorkflowRuntime()
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
        partial(
            request_send_mail_approval_node,
            usecases=usecases,
            workflow_runtime=active_workflow_runtime,
        ),
    )
    graph.add_node(
        "send_mail",
        partial(send_mail_node, usecases=usecases, workflow_runtime=active_workflow_runtime),
    )
    graph.add_node(
        "reject_send_mail",
        partial(
            reject_send_mail_node,
            usecases=usecases,
            workflow_runtime=active_workflow_runtime,
        ),
    )
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
    workflow_runtime: WorkflowRuntime | None = None,
) -> Any:
    repository = artifact_repository or InMemoryArtifactRepository()
    processing_record_store = InMemoryProcessingRecordStore()
    workflow_queue = InMemoryWorkflowQueue()
    workflow_usecases = usecases or RepositoryBackedDocumentUsecases(
        artifact_repository=repository,
        llm_gateway=StubDocumentLlmGateway(
            summary_response="Stub summary for unsettled items.",
            answer_response="Stub answer for document question.",
        ),
        processing_record_store=processing_record_store,
        vector_store=InMemoryVectorStore(),
    )
    return build_document_workflow(
        usecases=workflow_usecases,
        artifact_repository=repository,
        workflow_runtime=workflow_runtime
        or WorkflowRuntime(
            processing_record_store=processing_record_store,
            workflow_queue=workflow_queue,
        ),
    )


def invoke_document_workflow(
    user_input: str,
    human_decisions: list[HumanDecision] | None = None,
    workflow: Any | None = None,
) -> WorkflowState:
    active_workflow = workflow or create_document_workflow()
    initial_state: WorkflowState = {"user_input": user_input}
    if human_decisions:
        initial_state["human_decisions"] = human_decisions
    return cast(WorkflowState, active_workflow.invoke(initial_state))


def workflow_state_to_response(state: WorkflowState) -> dict[str, object]:
    response: dict[str, object] = {
        "flow": state.get("flow", "unknown"),
        "current_step": state.get("current_step", ""),
        "result": state.get("result"),
        "error": state.get("error"),
        "source_refs": state.get("source_refs", []),
        "unit_refs": state.get("unit_refs", []),
        "bundle_refs": state.get("bundle_refs", []),
        "dataset_refs": state.get("dataset_refs", []),
        "output_refs": state.get("output_refs", []),
    }
    if "pending_human_decision" in state:
        response["pending_human_decision"] = state["pending_human_decision"]
    return response
