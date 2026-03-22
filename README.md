# docflow-agent

다양한 입력 소스를 Agent와 usecase로 오케스트레이션하고, `source -> unit -> bundle` 모델로 확장할 수 있도록 만든 문서 처리 프레임워크입니다.

## 아키텍처

이 프로젝트는 선형 파이프라인보다 usecase 중심 오케스트레이션을 따릅니다.

```text
inbound -> usecases
usecases -> core
usecases -> outbound
```

- `inbound`: FastAPI, Streamlit, LangGraph, CLI 진입점
- `usecases`: 소스 조회, core 호출, outbound 호출, 결과 조합
- `core`: source kind 판단, unit 파싱, category 판단, bundle 결합, 분석, 규칙
- `outbound`: ECM, files, mail, SAP, OCR, LLM, DB 같은 외부 연동
- `types`: source, unit, bundle, external record, result 같은 실데이터 구조

핵심 개념도 바뀌었습니다.

- `source`: 입력 원천. ECM 파일, 메일 본문/첨부, SAP/API 데이터
- `unit`: 처리 단위. Excel sheet, PDF page group, image set, API record
- `bundle`: 여러 unit을 비즈니스 목적에 맞게 합친 구조
- `category`: business meaning. 예: invoice, settlement

core는 구조화된 타입만 다루고 outbound를 전혀 모릅니다. outbound는 외부 응답, 파일, bytes, API 호출을 책임집니다.

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
  types/
```

현재 구현된 최소 흐름은 Excel source를 읽어 sheet unit으로 파싱하고, invoice category를 식별한 뒤 invoice bundle로 결합하고 accounting rule을 검증하는 흐름입니다.

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
