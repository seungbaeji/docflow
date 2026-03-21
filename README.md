# docflow-agent

다양한 문서 처리 업무를 Agent를 통해 오케스트레이션하고, 필요한 기능을 직접 추가하며 확장할 수 있도록 만든 문서 처리 프레임워크입니다.

## 아키텍처

프로젝트는 아래 흐름을 따릅니다.

`inbound -> usecases -> core -> outbound`

- `inbound`: FastAPI, Streamlit, LangGraph 진입점
- `usecases`: 오케스트레이션만 담당
- `core`: 문서 분류, 파싱, 비즈니스 규칙
- `outbound`: 외부 연동과 파일 로딩 스텁
- `types`: 공용 dataclass 타입

비즈니스 로직은 모두 `core`에 둡니다. LangGraph 노드와 툴은 usecase만 호출하며 문서 처리 로직을 직접 구현하지 않습니다.

현재 프로젝트에는 실제 외부 시스템 연동 대신 스텁 구현이 포함되어 있으며, 문서 해석과 규칙 처리를 중심으로 로컬에서 쉽게 테스트하고 확장할 수 있게 구성되어 있습니다.

## example

프로젝트 루트의 [`example/process_excel_invoice.py`](/Users/seungbaeji/Workspace/posco/docflow/example/process_excel_invoice.py) 예시로 현재 제공되는 문서 처리 usecase를 바로 실행해볼 수 있습니다.

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
