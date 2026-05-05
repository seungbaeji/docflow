from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from docflow_agent.types.boundary.base import BoundaryModel
from docflow_agent.workflow.state import HumanDecision


class HumanDecisionRequest(BoundaryModel):
    decision_id: str = Field(min_length=1)
    kind: Literal["confirm", "select", "approve", "edit", "reject"]
    message: str = Field(min_length=1)
    options: list[str] = Field(min_length=1)
    selected: str | None = None
    payload: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_selected_option(self) -> "HumanDecisionRequest":
        if self.selected is not None and self.selected not in self.options:
            raise ValueError("selected must be one of options")
        return self

    def to_workflow_decision(self) -> HumanDecision:
        return {
            "decision_id": self.decision_id,
            "kind": self.kind,
            "message": self.message,
            "options": list(self.options),
            "selected": self.selected,
            "payload": dict(self.payload) if self.payload is not None else None,
        }


class ProcessRequest(BoundaryModel):
    user_input: str = Field(min_length=1)
    human_decisions: list[HumanDecisionRequest] | None = None

    def to_workflow_human_decisions(self) -> list[HumanDecision] | None:
        if self.human_decisions is None:
            return None
        return [decision.to_workflow_decision() for decision in self.human_decisions]
