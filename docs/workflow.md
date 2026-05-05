# Workflow

`workflow`는 특정 framework 이름이 아니라, 문서 처리 요청의 실행 흐름을 관리하는 오케스트레이션 객체를 뜻합니다.

이 프로젝트에서 workflow의 책임은 다음과 같습니다.

- 사용자 입력이나 상위 요청을 받아 어떤 흐름을 실행할지 결정
- 현재 단계와 다음 단계를 관리
- 필요한 usecase를 올바른 순서로 호출
- 대용량 데이터는 state에 넣지 않고 repository/store의 참조만 state에 유지
- human-in-the-loop 분기에서 `pending`, `approve`, `reject`, `resume` 상태를 관리
- 최종 결과나 다음 액션을 상위 진입점에 반환

즉 workflow는 `tool`보다 상태를 더 오래 들고 가는 실행 단위이며, `usecase`보다 상위에서 여러 단계를 연결합니다.

## Workflow와 Tool의 차이

- `tool`: stateless 외부 진입점
- `workflow`: state/context를 관리하는 실행 흐름

tool은 요청을 받아 workflow를 호출할 수 있지만, 자체적으로 큰 문맥이나 중간 산출물을 오래 보관하지 않습니다.

## Workflow와 Usecase의 차이

- `usecase`: 한 비즈니스 작업을 orchestration
- `workflow`: 여러 usecase를 단계적으로 연결하고 흐름을 제어

예를 들어 다음은 usecase 단위가 아니라 workflow 단위 책임입니다.

- prompt를 보고 `document_process`와 `document_to_mail` 중 어떤 flow인지 선택
- approval이 없으면 멈추고 `pending_human_decision`을 남김
- approval이 들어오면 같은 문맥으로 재개

반면 다음은 usecase 단위 책임입니다.

- source artifact 저장
- unit artifact 생성
- bundle 분석
- mail draft 생성

## Workflow와 State

workflow는 state를 갖지만, state는 큰 데이터를 직접 담지 않습니다.

state에는 다음만 들어갑니다.

- 현재 flow 이름
- 현재 step
- artifact ref 목록
- 선택된 ref
- human decision 상태
- 작은 결과 문자열 또는 에러

워크북, OCR 본문, 데이터프레임, 첨부 bytes 같은 큰 데이터는 repository/store에 있어야 합니다.

## Workflow와 LangGraph의 관계

현재 구현에서는 LangGraph가 workflow를 실행하는 엔진입니다.

하지만 개념적으로는:

- `workflow`: 도메인에 가까운 오케스트레이션 개념
- `LangGraph`: 그 workflow를 실행하는 현재 기술 구현

따라서 workflow 테스트는 “LangGraph 라이브러리 자체를 테스트”하는 것이 아니라, graph가 표현하는 흐름과 상태 전이가 우리 의도대로 동작하는지를 검증합니다.

## 테스트 관점

workflow 테스트는 보통 `unit` 성격입니다.

검증 대상:

- route 선택
- step 전이
- artifact ref 생성
- state safety
- human approval pending / approve / reject 흐름

이 테스트는 `tests/unit/workflow/` 아래에 두는 것이 가장 자연스럽습니다.

