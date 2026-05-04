from typing import Any, Literal, TypedDict

ArtifactKind = Literal[
    "source",
    "unit",
    "bundle",
    "dataset",
    "analysis",
    "draft",
    "result",
]

FlowName = Literal[
    "document_process",
    "document_to_mail",
    "unknown",
]

HumanDecisionKind = Literal[
    "confirm",
    "select",
    "approve",
    "edit",
    "reject",
]


class ArtifactRef(TypedDict):
    kind: ArtifactKind
    ref_id: str


class HumanDecision(TypedDict):
    decision_id: str
    kind: HumanDecisionKind
    message: str
    options: list[str]
    selected: str | None
    payload: dict[str, Any] | None


class WorkflowState(TypedDict, total=False):
    user_input: str
    flow: FlowName
    current_step: str

    source_refs: list[ArtifactRef]
    unit_refs: list[ArtifactRef]
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
