from typing import Any, Protocol


class ArtifactRepository(Protocol):
    def save(
        self,
        kind: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        ...

    def load(
        self,
        kind: str,
        ref_id: str,
    ) -> Any:
        ...

    def delete(
        self,
        kind: str,
        ref_id: str,
    ) -> None:
        ...

    def find(
        self,
        kind: str,
        filters: dict[str, Any] | None = None,
    ) -> list[str]:
        ...

