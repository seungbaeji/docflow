# LLM outbound

`src/docflow_agent/outbound/external/llm.py`는 Agent가 사용할 LLM 접근을 outbound 레이어에 격리합니다.

## 목적

- LangGraph 노드와 tool에서 모델 세부사항을 숨김
- 로컬 테스트에서는 stub 모델로 동작
- 운영 환경에서는 provider 설정만 바꿔 실제 모델로 연결
- usecase가 필요할 때만 호출되고 core는 LLM에 의존하지 않음
- 문서 해석 보조는 가능하지만 business rule의 source of truth가 되지 않음

## 제공 기능

- `build_llm_client`: 설정 기반 LLM client 생성
- `chat_text`: 일반 chat message 실행
- `summarize_document`: 문서 payload 요약
- `ask_document_question`: 문서 payload 기반 질의응답

## 설정

환경변수 prefix는 `DOCFLOW_AGENT_`입니다. 설정 모델은 `src/docflow_agent/config/settings.py`에 있고, 시스템 프롬프트 기본값은 `src/docflow_agent/config/prompt.py`에서 관리합니다. 환경변수는 nested `BaseModel` 구조를 사용하므로 `__` 구분자를 사용합니다.

- `DOCFLOW_AGENT_APP__NAME`
- `DOCFLOW_AGENT_APP__TITLE`
- `DOCFLOW_AGENT_APP__ENV`
- `DOCFLOW_AGENT_APP__DEBUG`
- `DOCFLOW_AGENT_API__HOST`
- `DOCFLOW_AGENT_API__PORT`
- `DOCFLOW_AGENT_API__RELOAD`
- `DOCFLOW_AGENT_LLM__PROVIDER`
- `DOCFLOW_AGENT_LLM__MODEL`
- `DOCFLOW_AGENT_LLM__TEMPERATURE`
- `DOCFLOW_AGENT_LLM__BASE_URL`
- `DOCFLOW_AGENT_LLM__TIMEOUT_SECONDS`
- `DOCFLOW_AGENT_LLM__MAX_RETRIES`
- `DOCFLOW_AGENT_LLM__RETRY_BACKOFF_SECONDS`
- `DOCFLOW_AGENT_LLM__RETRY_BACKOFF_MULTIPLIER`
- `DOCFLOW_AGENT_LLM__RETRY_ON_RATE_LIMIT`
- `DOCFLOW_AGENT_LLM__API_KEY`

기본값은 `stub`이며, 외부 서비스 없이도 로컬에서 실행됩니다. `openai`와 `gemini`는 모두 API key가 필요합니다.

`MAX_RETRIES`와 backoff 설정은 outbound wrapper의 재시도 정책에도 사용됩니다. 현재 기본 동작은 다음과 같습니다.

- quota 초과: `LlmQuotaExceededError`로 분류, 재시도하지 않음
- 일시적 rate limit: `LlmRateLimitError`로 분류, 설정에 따라 재시도 가능
- 기타 provider 실패: `LlmRequestError`

API key는 환경변수나 `pydantic-settings` 입력으로만 주입합니다. 런타임에 임시 파일을 fallback으로 읽지는 않습니다.

루트의 [.env.example](/Users/seungbaeji/Workspace/posco/docflow/.env.example:1)에 기본 예시를 추가해 두었습니다.

## 역할 경계

- `core`: category, analyze, rules 같은 결정 로직
- `usecases`: LLM 호출 여부 결정
- `outbound/external/llm`: 실제 provider 연결과 메시지 호출

LLM은 보조 해석이나 설명에 사용할 수 있지만, 회계 규칙이나 확정 판정 로직은 여전히 core에 있어야 합니다.

## 사용 예시

```python
from docflow_agent.outbound.external.llm import ask_document_question, chat_text, summarize_document

reply = chat_text("안녕하세요. 간단히 자기소개해줘")

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

## provider 메모

- `openai`: `langchain-openai`가 필요합니다.
- `gemini`: `langchain-google-genai`가 필요합니다.
- OpenAI 호환 gateway를 쓸 때는 `DOCFLOW_AGENT_LLM__PROVIDER=openai`와 `DOCFLOW_AGENT_LLM__BASE_URL` 조합으로 맞출 수 있습니다.

## API surface

FastAPI entrypoint는 `POST /chat` endpoint를 제공합니다. system prompt는 backend의 `src/docflow_agent/config/prompt.py`에서 관리하고, 대화 히스토리는 backend가 `session_id`별로 LangChain chat history로 관리합니다.

입력:

```json
{
  "message": "이어서 한 문장 더 설명해줘",
  "session_id": "session-001"
}
```

출력:

```json
{
  "session_id": "session-001",
  "message": "...",
  "provider": "gemini",
  "model": "gemini-2.0-flash"
}
```

에러 응답도 구분됩니다.

- quota 초과: HTTP `429`
- 일시적 rate limit / provider 요청 실패: HTTP `503`
