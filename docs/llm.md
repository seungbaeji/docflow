# LLM outbound

`src/docflow_agent/outbound/llm.py`는 Agent가 사용할 LLM 접근을 outbound 레이어에 격리합니다.

## 목적

- LangGraph 노드와 tool에서 모델 세부사항을 숨김
- 로컬 테스트에서는 stub 모델로 동작
- 운영 환경에서는 provider 설정만 바꿔 실제 모델로 연결
- usecase가 필요할 때만 호출되고 core는 LLM에 의존하지 않음
- 문서 해석 보조는 가능하지만 business rule의 source of truth가 되지 않음

## 제공 기능

- `build_llm_client`: 설정 기반 LLM client 생성
- `summarize_document`: 문서 payload 요약
- `ask_document_question`: 문서 payload 기반 질의응답

## 설정

환경변수 prefix는 `DOCFLOW_AGENT_`입니다.

- `DOCFLOW_AGENT_LLM_PROVIDER`: `stub` 또는 `openai`
- `DOCFLOW_AGENT_LLM_MODEL`: 모델 이름
- `DOCFLOW_AGENT_LLM_TEMPERATURE`: temperature
- `DOCFLOW_AGENT_LLM_API_KEY`: provider API key (`openai`일 때만 필요)

기본값은 `stub`이며, 외부 서비스 없이도 로컬에서 실행됩니다. `DOCFLOW_AGENT_LLM_PROVIDER=openai`를 사용할 때만 API key가 필요합니다.

## 역할 경계

- `core`: category, analyze, rules 같은 결정 로직
- `usecases`: LLM 호출 여부 결정
- `outbound/llm`: 실제 provider 연결과 메시지 호출

LLM은 보조 해석이나 설명에 사용할 수 있지만, 회계 규칙이나 확정 판정 로직은 여전히 core에 있어야 합니다.

## 사용 예시

```python
from docflow_agent.outbound.llm import ask_document_question, summarize_document

summary = summarize_document(
    {
        "source_kind": "excel",
        "category": "invoice",
        "invoice_number": "INV-001",
        "unit_count": 3,
    }
)

answer = ask_document_question(
    question="invoice number가 뭐야?",
    payload={"invoice_number": "INV-001"},
)
```
