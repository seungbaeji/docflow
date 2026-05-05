from __future__ import annotations

from typing import Literal

from docflow_agent.types.value.workflow import ArtifactKind, ArtifactRef
from docflow_agent.workflow.state import WorkflowState


ArtifactRefListKey = Literal[
    "source_refs",
    "unit_refs",
    "bundle_refs",
    "dataset_refs",
    "output_refs",
]


def artifact_ref(kind: ArtifactKind, ref_id: str) -> ArtifactRef:
    return {"kind": kind, "ref_id": ref_id}


def append_artifact_ref(state: WorkflowState, key: ArtifactRefListKey, ref: ArtifactRef) -> None:
    refs = list(state.get(key, []))
    refs.append(ref)
    state[key] = refs
