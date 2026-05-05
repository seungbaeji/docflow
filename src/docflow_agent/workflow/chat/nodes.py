from __future__ import annotations

from collections.abc import Callable

from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.session_context import SessionDocumentStore
from docflow_agent.types.value.results import UsecaseOutcome
from docflow_agent.workflow.chat.state import State


def resolve_source_node(
    state: State,
    *,
    source_from_upload: Callable[[str], str],
    session_document_store: SessionDocumentStore,
) -> State:
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


def prepare_node(
    state: State,
    *,
    parse_units: Callable[[str], list[str]],
    categorize_units: Callable[[list[str]], list[str]],
    combine_bundle: Callable[[list[str]], str],
    analyze: Callable[[str], UsecaseOutcome],
    artifact_repository: ArtifactRepository,
) -> State:
    source_ref_id = state["source_ref_id"]

    parsed_refs = artifact_repository.find("unit", {"source_ref_id": source_ref_id, "stage": "parsed"})
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
