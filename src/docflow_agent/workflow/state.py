from typing import TypedDict

from docflow_agent.types.value.workflow import ArtifactRef, FlowName, HumanDecision


class WorkflowState(TypedDict, total=False):
    user_input: str
    flow: FlowName
    current_step: str

    source_refs: list[ArtifactRef]
    unit_refs: list[ArtifactRef]
    categorized_unit_refs: list[ArtifactRef]
    bundle_refs: list[ArtifactRef]
    dataset_refs: list[ArtifactRef]
    output_refs: list[ArtifactRef]

    selected_source_ref: ArtifactRef
    selected_unit_ref: ArtifactRef
    selected_bundle_ref: ArtifactRef

    pending_human_decision: HumanDecision
    human_decisions: list[HumanDecision]

    result: str
    error: str
