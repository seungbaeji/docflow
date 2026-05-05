from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docflow_agent.errors import StorageIntegrationError
from docflow_agent.types.boundary.external import StoredObject


@dataclass(frozen=True)
class StorageClient:
    root_dir: str


def store_bytes(
    client: StorageClient,
    relative_path: str,
    payload: bytes,
    content_type: str,
    metadata: dict[str, object] | None = None,
) -> StoredObject:
    path = Path(client.root_dir) / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return StoredObject(
        location=str(path),
        content_type=content_type,
        size_bytes=len(payload),
        metadata=dict(metadata or {}),
    )


def load_bytes(client: StorageClient, relative_path: str) -> bytes:
    path = Path(client.root_dir) / relative_path
    if not path.is_file():
        raise StorageIntegrationError(str(path))
    return path.read_bytes()
