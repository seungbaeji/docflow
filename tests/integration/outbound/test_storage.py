from pathlib import Path

import pytest

from docflow_agent.errors import StorageIntegrationError
from docflow_agent.outbound.external.storage import StorageClient, load_bytes, store_bytes


def test_store_and_load_bytes(tmp_path: Path) -> None:
    client = StorageClient(root_dir=str(tmp_path))

    stored = store_bytes(
        client=client,
        relative_path="incoming/invoice.pdf",
        payload=b"pdf-binary",
        content_type="application/pdf",
        metadata={"source": "ecm"},
    )

    assert stored.size_bytes == 10
    assert stored.metadata == {"source": "ecm"}
    assert load_bytes(client, "incoming/invoice.pdf") == b"pdf-binary"


def test_load_bytes_raises_for_missing_object(tmp_path: Path) -> None:
    client = StorageClient(root_dir=str(tmp_path))

    with pytest.raises(StorageIntegrationError, match="missing.pdf"):
        load_bytes(client, "missing.pdf")
