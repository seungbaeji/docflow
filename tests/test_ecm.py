import json
from email.message import Message
from pathlib import Path
from typing import cast
from urllib.request import Request

import pytest
from pytest import MonkeyPatch

from docflow_agent.outbound import ecm
from docflow_agent.outbound.ecm import (
    EcmClient,
    compute_sha256_digest,
    create_hmac_signature,
    download_document,
    search_documents,
    upload_document,
    verify_hmac_signature,
)
from docflow_agent.errors import EcmResponseError
from docflow_agent.types.common import EcmAuth, EcmSearchQuery, FileInfo


class FakeResponse:
    def __init__(self, payload: bytes, content_type: str = "application/json") -> None:
        self._payload = payload
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


def test_compute_sha256_digest_is_deterministic() -> None:
    assert (
        compute_sha256_digest(b"invoice")
        == "52d6e3de4fa0dcc29946695f93940c3e7f26f30e1e39f4b1a49ad98839112786"
    )


def test_hmac_signature_round_trip() -> None:
    message = "POST\n/documents/search\nabc123"
    signature = create_hmac_signature(secret="secret-key", message=message)

    assert verify_hmac_signature(secret="secret-key", message=message, signature=signature) is True


def test_search_documents_builds_signed_request(monkeypatch: MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        request_data = request.data
        captured["body"] = request_data.decode("utf-8") if isinstance(request_data, bytes) else None
        captured["timeout"] = timeout
        return FakeResponse(
            json.dumps(
                {
                    "items": [
                        {
                            "document_id": "doc-001",
                            "name": "invoice.xlsx",
                            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "metadata": {"source": "ecm"},
                        }
                    ]
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr(ecm, "urlopen", fake_urlopen)

    documents = search_documents(
        client=EcmClient(
            base_url="https://ecm.example.com",
            auth=EcmAuth(api_key="key", api_secret="secret", tenant_id="tenant-a"),
        ),
        query=EcmSearchQuery(text="invoice", filters={"status": "active"}),
    )

    assert len(documents) == 1
    assert documents[0].document_id == "doc-001"
    assert captured["url"] == "https://ecm.example.com/documents/search"
    headers = cast(dict[str, str], captured["headers"])
    assert "x-ecm-signature" in {key.lower() for key in headers}
    assert json.loads(str(captured["body"])) == {
        "filters": {"status": "active"},
        "limit": 20,
        "offset": 0,
        "query": "invoice",
    }


def test_download_document_writes_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        response = FakeResponse(b"spreadsheet-bytes", content_type="application/octet-stream")
        response.headers["Content-Disposition"] = 'attachment; filename="invoice.xlsx"'
        return response

    monkeypatch.setattr(ecm, "urlopen", fake_urlopen)

    file_info = download_document(
        client=EcmClient(base_url="https://ecm.example.com"),
        document_id="doc-001",
        destination_dir=str(tmp_path),
    )

    assert file_info.name == "invoice.xlsx"
    assert Path(file_info.path).read_bytes() == b"spreadsheet-bytes"


def test_download_document_sanitizes_filename(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        response = FakeResponse(b"spreadsheet-bytes", content_type="application/octet-stream")
        response.headers["Content-Disposition"] = 'attachment; filename="../invoice.xlsx"'
        return response

    monkeypatch.setattr(ecm, "urlopen", fake_urlopen)

    file_info = download_document(
        client=EcmClient(base_url="https://ecm.example.com"),
        document_id="doc-001",
        destination_dir=str(tmp_path),
    )

    assert file_info.name == "invoice.xlsx"
    assert Path(file_info.path).parent == tmp_path


def test_upload_document_posts_file_bytes(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    source_path = tmp_path / "invoice.xlsx"
    source_path.write_bytes(b"fake-binary")

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        captured["headers"] = dict(request.header_items())
        captured["body"] = request.data
        return FakeResponse(
            json.dumps(
                {
                    "document_id": "uploaded-001",
                    "name": "invoice.xlsx",
                    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "metadata": {"folder": "invoices"},
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr(ecm, "urlopen", fake_urlopen)

    uploaded = upload_document(
        client=EcmClient(base_url="https://ecm.example.com"),
        file_info=FileInfo(
            name="invoice.xlsx",
            path=str(source_path),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        metadata={"folder": "invoices"},
    )

    assert uploaded.document_id == "uploaded-001"
    assert captured["body"] == b"fake-binary"
    headers = cast(dict[str, str], captured["headers"])
    assert headers["X-file-name"] == "invoice.xlsx"
    assert headers["X-metadata"] == '{"folder": "invoices"}'


def test_upload_document_requires_document_id(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    source_path = tmp_path / "invoice.xlsx"
    source_path.write_bytes(b"fake-binary")

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        return FakeResponse(b"", content_type="application/json")

    monkeypatch.setattr(ecm, "urlopen", fake_urlopen)

    with pytest.raises(EcmResponseError, match="document_id"):
        upload_document(
            client=EcmClient(base_url="https://ecm.example.com"),
            file_info=FileInfo(
                name="invoice.xlsx",
                path=str(source_path),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            metadata={"folder": "invoices"},
        )


def test_ecm_auth_repr_redacts_credentials() -> None:
    auth = EcmAuth(
        api_key="key-123",
        api_secret="secret-456",
        access_token="token-789",
        tenant_id="tenant-a",
    )

    rendered = repr(auth)

    assert "key-123" not in rendered
    assert "secret-456" not in rendered
    assert "token-789" not in rendered
    assert "tenant-a" in rendered
