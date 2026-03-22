# ECM outbound

`src/docflow_agent/outbound/ecm.py`는 특정 벤더 SDK에 묶이지 않는 범용 ECM HTTP 클라이언트를 제공합니다.

ECM은 이 프로젝트에서 source를 가져오거나 결과 파일을 다시 저장하는 outbound 역할을 맡습니다. business category 판단, bundle 조합, edit intent 생성은 여기서 하지 않습니다.

## 제공 기능

- `compute_sha256_digest`: 요청 본문 무결성 체크용 SHA-256 digest 생성
- `create_hmac_signature`: API secret 기반 HMAC-SHA256 서명 생성
- `verify_hmac_signature`: 서명 검증
- `search_documents`: ECM 검색 API 호출
- `download_document`: 문서 다운로드 후 로컬 저장
- `upload_document`: 로컬 파일 업로드
- `fetch_from_ecm`: 다운로드 기능을 감싼 단순 helper

## 역할 경계

- `core`: 어떤 문서를 찾아야 하는지, 어떤 수정이 필요한지 판단
- `usecases`: ECM 검색/다운로드/업로드 시점 orchestration
- `outbound/ecm`: 실제 HTTP 요청, 응답 파싱, 파일 저장/업로드 실행

ECM은 문서 수정의 실행 결과를 다시 저장하는 용도로도 사용할 수 있지만, 수정 규칙 자체를 알면 안 됩니다.

## 핵심 타입

- `EcmAuth`: API key, secret, bearer token, tenant 정보
- `EcmSearchQuery`: 검색어, 페이지네이션, 필터
- `EcmDocument`: ECM 문서 메타데이터
- `EcmClient`: base URL, endpoint path, timeout 설정

## 기본 요청 방식

서명이 필요한 경우 아래 헤더를 자동으로 붙입니다.

- `X-ECM-API-Key`
- `X-ECM-Content-SHA256`
- `X-ECM-Signature`
- `Authorization`
- `X-ECM-Tenant`

서명 메시지 포맷은 다음과 같습니다.

```text
{METHOD}
{PATH}
{SHA256_HEX_DIGEST}
```

## 사용 예시

```python
from docflow_agent.outbound.ecm import EcmClient, search_documents, upload_document
from docflow_agent.types.common import EcmAuth, EcmSearchQuery, FileInfo

client = EcmClient(
    base_url="https://ecm.example.com",
    auth=EcmAuth(
        api_key="client-key",
        api_secret="client-secret",
        access_token="token",
        tenant_id="tenant-a",
    ),
)

hits = search_documents(
    client=client,
    query=EcmSearchQuery(text="invoice", filters={"status": "active"}),
)

uploaded = upload_document(
    client=client,
    file_info=FileInfo(
        name="invoice.xlsx",
        path="fixtures/invoice.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    metadata={"folder": "invoices"},
)
```

## endpoint 기본값

- search: `/documents/search`
- upload: `/documents/upload`
- download: `/documents/{document_id}/download`

필요하면 `EcmClient` 생성 시 path를 바꿔 벤더별 API에 맞출 수 있습니다.
