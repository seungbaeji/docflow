from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.session_context import SessionDocumentStore
from docflow_agent.types.value.results import UsecaseOutcome
from docflow_agent.workflow.chat.nodes import prepare_node, resolve_source_node
from docflow_agent.workflow.chat.state import State


def build_workflow(
    *,
    source_from_upload: Callable[[str], str],
    parse_units: Callable[[str], list[str]],
    categorize_units: Callable[[list[str]], list[str]],
    combine_bundle: Callable[[list[str]], str],
    analyze: Callable[[str], UsecaseOutcome],
    artifact_repository: ArtifactRepository,
    session_document_store: SessionDocumentStore,
) -> Any:
    graph = StateGraph(State)
    graph.add_node(
        "resolve_source",
        lambda state: resolve_source_node(
            state,
            source_from_upload=source_from_upload,
            session_document_store=session_document_store,
        ),
    )
    graph.add_node(
        "prepare",
        lambda state: prepare_node(
            state,
            parse_units=parse_units,
            categorize_units=categorize_units,
            combine_bundle=combine_bundle,
            analyze=analyze,
            artifact_repository=artifact_repository,
        ),
    )
    graph.add_edge(START, "resolve_source")
    graph.add_edge("resolve_source", "prepare")
    graph.add_edge("prepare", END)
    return graph.compile()


def invoke_workflow(
    *,
    workflow: Any,
    session_id: str,
    message: str,
) -> State:
    return cast(State, workflow.invoke({"session_id": session_id, "message": message}))
