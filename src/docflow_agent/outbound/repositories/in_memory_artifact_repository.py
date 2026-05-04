from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _StoredArtifact:
    value: Any
    metadata: dict[str, Any]


class InMemoryArtifactRepository:
    def __init__(self) -> None:
        self._storage: dict[str, dict[str, _StoredArtifact]] = {}
        self._counters: dict[str, int] = {}

    def save(
        self,
        kind: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        next_index = self._counters.get(kind, 0) + 1
        self._counters[kind] = next_index
        ref_id = f"{kind}-{next_index:04d}"
        artifacts = self._storage.setdefault(kind, {})
        artifacts[ref_id] = _StoredArtifact(value=value, metadata=dict(metadata or {}))
        return ref_id

    def load(
        self,
        kind: str,
        ref_id: str,
    ) -> Any:
        artifact = self._storage.get(kind, {}).get(ref_id)
        if artifact is None:
            raise KeyError(f"Artifact not found for kind='{kind}' ref_id='{ref_id}'")
        return artifact.value

    def delete(
        self,
        kind: str,
        ref_id: str,
    ) -> None:
        artifacts = self._storage.get(kind, {})
        if ref_id not in artifacts:
            raise KeyError(f"Artifact not found for kind='{kind}' ref_id='{ref_id}'")
        del artifacts[ref_id]

    def find(
        self,
        kind: str,
        filters: dict[str, Any] | None = None,
    ) -> list[str]:
        wanted = filters or {}
        matches: list[str] = []
        for ref_id, artifact in self._storage.get(kind, {}).items():
            if all(artifact.metadata.get(key) == value for key, value in wanted.items()):
                matches.append(ref_id)
        return matches

