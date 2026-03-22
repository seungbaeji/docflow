import base64
import hashlib
import hmac
import json
from email.message import Message
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import quote, urljoin
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from docflow_agent.errors import EcmRequestError, EcmResponseError
from docflow_agent.types.common import EcmAuth, EcmSearchQuery, FileInfo
from docflow_agent.types.external import EcmDocument


class EcmClient:
    def __init__(
        self,
        base_url: str,
        auth: EcmAuth | None = None,
        timeout_seconds: float = 30.0,
        search_path: str = "/documents/search",
        upload_path: str = "/documents/upload",
        download_path_template: str = "/documents/{document_id}/download",
    ) -> None:
        self.base_url = base_url
        self.auth = auth
        self.timeout_seconds = timeout_seconds
        self.search_path = search_path
        self.upload_path = upload_path
        self.download_path_template = download_path_template


class HttpResponse(Protocol):
    headers: Message

    def read(self) -> bytes: ...


def compute_sha256_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def create_hmac_signature(secret: str, message: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def verify_hmac_signature(secret: str, message: str, signature: str) -> bool:
    expected = create_hmac_signature(secret=secret, message=message)
    return hmac.compare_digest(expected, signature)


def search_documents(client: EcmClient, query: EcmSearchQuery) -> list[EcmDocument]:
    payload = {
        "query": query.text,
        "limit": query.limit,
        "offset": query.offset,
        "filters": query.filters,
    }
    response = _request_json(
        client=client,
        method="POST",
        path=client.search_path,
        payload=payload,
    )
    raw_hits = response.get("items", [])
    hits = raw_hits if isinstance(raw_hits, list) else []
    return [_parse_ecm_document(item) for item in hits if isinstance(item, dict)]


def download_document(client: EcmClient, document_id: str, destination_dir: str) -> FileInfo:
    path = client.download_path_template.format(document_id=quote(document_id, safe=""))
    response, payload = _request_bytes(client=client, method="GET", path=path)

    headers = response.headers
    file_name = _safe_filename(_extract_filename(headers)) or f"{document_id}.bin"
    content_type = headers.get_content_type() or "application/octet-stream"

    destination_path = Path(destination_dir) / file_name
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_bytes(payload)

    return FileInfo(name=file_name, path=str(destination_path), content_type=content_type)


def upload_document(
    client: EcmClient,
    file_info: FileInfo,
    metadata: dict[str, object] | None = None,
) -> EcmDocument:
    file_bytes = Path(file_info.path).read_bytes()
    headers = {
        "Content-Type": file_info.content_type,
        "X-File-Name": file_info.name,
    }
    if metadata:
        headers["X-Metadata"] = json.dumps(metadata, sort_keys=True)

    response = _request_json(
        client=client,
        method="POST",
        path=client.upload_path,
        payload=file_bytes,
        extra_headers=headers,
        expect_json=False,
    )
    raw_document_id = response.get("document_id")
    if not isinstance(raw_document_id, str) or not raw_document_id:
        raise EcmResponseError(
            path=client.upload_path,
            reason="Upload response did not include a document_id",
        )
    return _parse_ecm_document(
        {
            "document_id": raw_document_id,
            "name": response.get("name", file_info.name),
            "content_type": response.get("content_type", file_info.content_type),
            "metadata": response.get("metadata", metadata or {}),
        }
    )


def fetch_from_ecm(client: EcmClient, document_id: str, destination_dir: str) -> FileInfo:
    return download_document(client=client, document_id=document_id, destination_dir=destination_dir)


def _request_json(
    client: EcmClient,
    method: str,
    path: str,
    payload: dict[str, object] | bytes | None = None,
    extra_headers: dict[str, str] | None = None,
    expect_json: bool = True,
) -> dict[str, object]:
    response, body = _request_bytes(
        client=client,
        method=method,
        path=path,
        payload=payload,
        extra_headers=extra_headers,
    )

    if not body:
        return {}

    if not expect_json and response.headers.get_content_type() != "application/json":
        return {}

    try:
        loaded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EcmResponseError(path=path, reason=str(exc)) from exc
    if not isinstance(loaded, dict):
        raise EcmResponseError(path=path, reason="Expected JSON object response")
    return cast(dict[str, object], loaded)


def _request_bytes(
    client: EcmClient,
    method: str,
    path: str,
    payload: dict[str, object] | bytes | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[HttpResponse, bytes]:
    request_body = _encode_payload(payload)
    headers = _build_headers(
        method=method,
        path=path,
        payload=request_body,
        auth=client.auth,
        extra_headers=extra_headers,
    )
    url = urljoin(client.base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url=url, data=request_body, headers=headers, method=method)

    try:
        with urlopen(request, timeout=client.timeout_seconds) as response:
            body = response.read()
            return response, body
    except HTTPError as exc:
        raise EcmRequestError(method=method, path=path, reason=f"HTTP {exc.code}") from exc
    except URLError as exc:
        raise EcmRequestError(method=method, path=path, reason=str(exc.reason)) from exc


def _encode_payload(payload: dict[str, object] | bytes | None) -> bytes | None:
    if payload is None:
        return None
    if isinstance(payload, bytes):
        return payload
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def _build_headers(
    method: str,
    path: str,
    payload: bytes | None,
    auth: EcmAuth | None,
    extra_headers: dict[str, str] | None,
) -> dict[str, str]:
    headers: dict[str, str] = {
        "Accept": "application/json",
    }
    if payload is not None and "Content-Type" not in (extra_headers or {}):
        headers["Content-Type"] = "application/json"

    if auth is not None:
        digest = compute_sha256_digest(payload or b"")
        message = "\n".join([method.upper(), path, digest])
        headers["X-ECM-API-Key"] = auth.api_key
        headers["X-ECM-Content-SHA256"] = digest
        headers["X-ECM-Signature"] = create_hmac_signature(auth.api_secret, message)
        if auth.access_token:
            headers["Authorization"] = f"Bearer {auth.access_token}"
        if auth.tenant_id:
            headers["X-ECM-Tenant"] = auth.tenant_id

    if extra_headers:
        headers.update(extra_headers)
    return headers


def _extract_filename(headers: Message) -> str | None:
    content_disposition = headers.get("Content-Disposition")
    if not content_disposition:
        return None
    marker = "filename="
    if marker not in content_disposition:
        return None
    return content_disposition.split(marker, maxsplit=1)[1].strip('"')


def _safe_filename(file_name: str | None) -> str | None:
    if not file_name:
        return None
    sanitized = Path(file_name).name
    if sanitized in {"", ".", ".."}:
        return None
    return sanitized


def _parse_ecm_document(item: dict[str, object]) -> EcmDocument:
    raw_metadata = item.get("metadata", {})
    metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
    return EcmDocument(
        document_id=str(item.get("document_id", "")),
        name=str(item.get("name", "")),
        content_type=str(item.get("content_type", "application/octet-stream")),
        metadata=cast(dict[str, object], metadata),
    )
