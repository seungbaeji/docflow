# docflow-agent

다양한 입력 소스를 Agent와 usecase로 오케스트레이션하고, `source -> unit -> bundle` 모델 위에서 문서 해석, 분석, 규칙 검증, 문서 수정 자동화까지 확장할 수 있도록 만든 문서 처리 프레임워크입니다.

## 아키텍처

이 프로젝트는 선형 파이프라인보다 usecase 중심 오케스트레이션을 따릅니다.

```text
inbound -> usecases
usecases -> core
usecases -> outbound
```

- `inbound`: FastAPI, Streamlit, LangGraph, CLI 진입점
- `usecases`: 소스 조회, core 호출, outbound 호출, 결과 조합, 저장/전달 orchestration
- `core`: source kind 판단, unit 파싱, category 판단, bundle 결합, 분석, 규칙, edit intent 생성
- `outbound`: ECM, files, mail, SAP, OCR, LLM, DB, Excel automation, RPA, COM 같은 외부 연동과 실행
- `types`: source, unit, bundle, external record, edit intent, result 같은 실데이터 구조

핵심 개념도 바뀌었습니다.

- `source`: 입력 원천. ECM 파일, 메일 본문/첨부, SAP/API 데이터
- `unit`: 처리 단위. Excel sheet, PDF page group, image set, API record
- `bundle`: 여러 unit을 비즈니스 목적에 맞게 합친 구조
- `category`: business meaning. 예: invoice, settlement
- `edit intent`: core가 결정한 수정 명세. 실제 파일/애플리케이션 수정은 outbound가 수행

core는 구조화된 타입만 다루고 outbound를 전혀 모릅니다. outbound는 외부 응답, 파일, bytes, API 호출뿐 아니라 문서 수정 실행과 애플리케이션 자동화까지 책임집니다.

## 프로젝트 구조

```text
src/docflow_agent/
  inbound/
  usecases/
  core/
    source_kind/
    parse/
    category/
    combine/
    analyze/
    edit/
    rules/
  outbound/
    document_automation.py
  types/
    edit.py
```

현재 구현된 최소 흐름은 Excel source를 읽어 sheet unit으로 파싱하고, invoice category를 식별한 뒤 invoice bundle로 결합하고 accounting rule을 검증하는 흐름입니다.

장기적으로는 여기서 끝나지 않고, core가 edit intent를 만들고 outbound가 openpyxl, Excel COM, 또는 RPA로 실제 수정을 실행하는 구조를 목표로 합니다.

## example

프로젝트 루트의 `example/process_excel_invoice.py` 예시로 source 기반 usecase를 바로 실행해볼 수 있습니다.
현재 예시는 outbound source 로더가 스텁이기 때문에 실제 파일을 읽지 않으며, 전달하는 location은 예시 식별자 역할만 합니다.

예시 실행:

```bash
uv run python example/process_excel_invoice.py
```

## 실행

개발 의존성을 포함해 설치한 뒤 아래 명령으로 테스트할 수 있습니다.

```bash
pytest
```

CLI 엔트리포인트는 다음과 같습니다.

- `app-process`
- `app-dev`
- `app-test`
- `app-docs`

## 문서 수정과 자동화

문서 수정은 두 단계로 나뉩니다.

- `core/edit`: 무엇을 바꿔야 하는지 결정하고 edit intent를 생성
- `outbound`: edit intent를 실제 문서나 애플리케이션에 적용

즉, 셀 값을 바꿔야 하는지, 어떤 시트를 추가해야 하는지, 어떤 재계산이 필요한지는 core가 판단하고, 실제 openpyxl 처리나 Excel COM/RPA 실행은 outbound가 맡습니다.

기본 원칙은 다음과 같습니다.

- 기본값은 파일 레벨 처리
- 애플리케이션 자동화는 파일 레벨 처리로 해결할 수 없을 때만 사용
- workbook, worksheet, COM 객체, UI automation 객체는 outbound 밖으로 나오지 않음

## 배포

PyPI 배포용 GitHub Actions workflow는 `.github/workflows/publish-pypi.yml`에 있습니다.

- 기본 동작은 `push` 시 자동 배포가 아니라 `release published` 또는 수동 실행입니다.
- release 기반 배포는 `main`을 대상으로 만든 release일 때만 publish 합니다.
- publish job은 먼저 패키지를 build 하고 `twine check`로 검증한 뒤 PyPI에 업로드합니다.
- 인증은 GitHub Actions trusted publishing 기준입니다. PyPI 프로젝트에서 GitHub repository와 environment `pypi`를 연결해 두어야 합니다.
