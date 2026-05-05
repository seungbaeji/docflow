from __future__ import annotations

from typing import Any, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.session_context import SessionDocumentStore
from docflow_agent.types.value.document import DocumentPayload
from docflow_agent.workflow.document_services import DocumentWorkflowServices


class DocumentChatState(TypedDict, total=False):
    session_id: str
    message: str
    source_ref_id: str


def build_document_chat_workflow(
    *,
    services: DocumentWorkflowServices,
    artifact_repository: ArtifactRepository,
    session_document_store: SessionDocumentStore,
) -> Any:
    graph = StateGraph(DocumentChatState)
    graph.add_node(
        "resolve_source",
        lambda state: _resolve_source_node(
            state,
            services=services,
            session_document_store=session_document_store,
        ),
    )
    graph.add_node(
        "prepare_document",
        lambda state: _prepare_document_node(state, services=services, artifact_repository=artifact_repository),
    )
    graph.add_edge(START, "resolve_source")
    graph.add_edge("resolve_source", "prepare_document")
    graph.add_edge("prepare_document", END)
    return graph.compile()


def invoke_document_chat_workflow(
    *,
    workflow: Any,
    session_id: str,
    message: str,
) -> DocumentChatState:
    return cast(
        DocumentChatState,
        workflow.invoke({"session_id": session_id, "message": message}),
    )


def _resolve_source_node(
    state: DocumentChatState,
    *,
    services: DocumentWorkflowServices,
    session_document_store: SessionDocumentStore,
) -> DocumentChatState:
    source_ref_id = session_document_store.get_current_source_ref(state["session_id"])
    if source_ref_id is None:
        upload_id = session_document_store.get_current_upload_id(state["session_id"])
        if upload_id is None:
            raise KeyError("No current upload or source is associated with the session")
        source_ref_id = services["source_from_upload"](upload_id)
        session_document_store.set_current_source_ref(state["session_id"], source_ref_id)
        session_document_store.clear_current_upload_id(state["session_id"])
    state["source_ref_id"] = source_ref_id
    return state


def _prepare_document_node(
    state: DocumentChatState,
    *,
    services: DocumentWorkflowServices,
    artifact_repository: ArtifactRepository,
) -> DocumentChatState:
    source_ref_id = state["source_ref_id"]
    parsed_refs = artifact_repository.find(
        "unit",
        {"source_ref_id": source_ref_id, "stage": "parsed"},
    )
    if not parsed_refs:
        parsed_refs = services["parse_units"](source_ref_id)

    categorized_refs = artifact_repository.find(
        "unit",
        {"source_ref_id": source_ref_id, "stage": "categorized"},
    )
    if not categorized_refs:
        categorized_refs = services["categorize_units"](parsed_refs)

    bundle_refs = artifact_repository.find(
        "bundle",
        {"source_ref_id": source_ref_id, "stage": "combined"},
    )
    if bundle_refs:
        bundle_ref_id = bundle_refs[-1]
    else:
        bundle_ref_id = services["combine_bundle"](categorized_refs)

    analysis_refs = artifact_repository.find(
        "analysis",
        {"bundle_ref_id": bundle_ref_id, "stage": "analyzed"},
    )
    if not analysis_refs:
        services["analyze"](bundle_ref_id)
    return state
