from typing import Any

from docflow_agent.workflow.document_workflow import create_document_workflow
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.workflow.document_services import bind_document_workflow_services


def _assert_no_unsafe_payloads(value: Any) -> None:
    assert not isinstance(value, bytes)
    if isinstance(value, dict):
        for nested_value in value.values():
            _assert_no_unsafe_payloads(nested_value)
    elif isinstance(value, list):
        for item in value:
            _assert_no_unsafe_payloads(item)


def test_workflow_state_contains_only_small_control_data_and_refs() -> None:
    repository = InMemoryArtifactRepository()
    workflow = create_document_workflow(
        usecases=bind_document_workflow_services(artifact_repository=repository),
        artifact_repository=repository,
    )

    state = workflow.invoke({"user_input": "엑셀 문서를 분석해줘"})

    for ref_group_name in ("source_refs", "unit_refs", "bundle_refs", "dataset_refs", "output_refs"):
        for ref in state.get(ref_group_name, []):
            assert set(ref.keys()) == {"kind", "ref_id"}
            assert isinstance(ref["kind"], str)
            assert isinstance(ref["ref_id"], str)

    for key in ("selected_source_ref", "selected_unit_ref", "selected_bundle_ref"):
        if key in state:
            assert set(state[key].keys()) == {"kind", "ref_id"}

    forbidden_keys = {"workbook", "worksheet", "dataframe", "rows", "bytes", "attachments", "mail_body"}
    assert forbidden_keys.isdisjoint(state.keys())
    _assert_no_unsafe_payloads(state)
