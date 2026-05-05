from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.session_context import SessionDocumentStore
from docflow_agent.types.value.results import UsecaseOutcome


class DocumentChatState(TypedDict, total=False):
    session_id: str
    message: str
    source_ref_id: str


def build_document_chat_workflow(
    *,
    source_from_upload: Callable[[str], str],
    parse_units: Callable[[str], list[str]],
    categorize_units: Callable[[list[str]], list[str]],
    combine_bundle: Callable[[list[str]], str],
    analyze: Callable[[str], UsecaseOutcome],
    artifact_repository: ArtifactRepository,
    session_document_store: SessionDocumentStore,
) -> Any:
    graph = StateGraph(DocumentChatState)
    graph.add_node(
        "resolve_source",
        lambda state: _resolve_source_node(
            state,
            source_from_upload=source_from_upload,
            session_document_store=session_document_store,
        ),
    )
    graph.add_node(
        "prepare_document",
        lambda state: _prepare_document_node(
            state,
            parse_units=parse_units,
            categorize_units=categorize_units,
            combine_bundle=combine_bundle,
            analyze=analyze,
            artifact_repository=artifact_repository,
        ),
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
    source_from_upload: Callable[[str], str],
    session_document_store: SessionDocumentStore,
) -> DocumentChatState:
    source_ref_id = session_document_store.get_current_source_ref(state["session_id"])
    if source_ref_id is None:
        upload_id = session_document_store.get_current_upload_id(state["session_id"])
        if upload_id is None:
            raise KeyError("No current upload or source is associated with the session")
        source_ref_id = source_from_upload(upload_id)
        session_document_store.set_current_source_ref(state["session_id"], source_ref_id)
        session_document_store.clear_current_upload_id(state["session_id"])
    state["source_ref_id"] = source_ref_id
    return state


def _prepare_document_node(
    state: DocumentChatState,
    *,
    parse_units: Callable[[str], list[str]],
    categorize_units: Callable[[list[str]], list[str]],
    combine_bundle: Callable[[list[str]], str],
    analyze: Callable[[str], UsecaseOutcome],
    artifact_repository: ArtifactRepository,
) -> DocumentChatState:
    source_ref_id = state["source_ref_id"]
    parsed_refs = artifact_repository.find(
        "unit",
        {"source_ref_id": source_ref_id, "stage": "parsed"},
    )
    if not parsed_refs:
        parsed_refs = parse_units(source_ref_id)

    categorized_refs = artifact_repository.find(
        "unit",
        {"source_ref_id": source_ref_id, "stage": "categorized"},
    )
    if not categorized_refs:
        categorized_refs = categorize_units(parsed_refs)

    bundle_refs = artifact_repository.find(
        "bundle",
        {"source_ref_id": source_ref_id, "stage": "combined"},
    )
    if bundle_refs:
        bundle_ref_id = bundle_refs[-1]
    else:
        bundle_ref_id = combine_bundle(categorized_refs)

    analysis_refs = artifact_repository.find(
        "analysis",
        {"bundle_ref_id": bundle_ref_id, "stage": "analyzed"},
    )
    if not analysis_refs:
        analyze(bundle_ref_id)
    return state
