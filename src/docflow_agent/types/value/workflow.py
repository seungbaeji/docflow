from __future__ import annotations

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
