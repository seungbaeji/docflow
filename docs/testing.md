# Testing Without Abstract Adapters

이 프로젝트는 `inbound`와 `outbound`를 위해 abstract interface를 먼저 정의하지 않습니다.

## 기본 입장

- 현재 복잡성의 중심은 provider abstraction이 아니라 문서 해석과 business rule입니다.
- 모든 경계를 interface로 추상화하면 코드량과 탐색 비용만 늘 수 있습니다.
- 대신 실제 모듈을 직접 테스트하고, 필요한 seam만 함수 호출 지점에서 제어합니다.

즉, 테스트 가능성은 다음 방식으로 확보합니다.

- 순수 함수 중심의 `core`
- 얇은 orchestration 역할의 `usecases`
- 작은 함수와 client로 나뉜 `outbound`
- `monkeypatch`, fake response, `tmp_path` 같은 로컬 테스트 도구

## 레이어별 테스트 방법

### core

`core`는 structured type을 받아 structured result를 돌려주는 순수 함수 중심으로 유지합니다.

- mock 없이 직접 호출
- dataclass 입력을 만들고 결과만 검증
- business rule과 category 판단을 집중적으로 테스트

예시:
- `tests/test_category_invoice.py`
- `tests/test_invoice_rule.py`
- `tests/test_edit_invoice.py`

### usecases

`usecases`는 orchestration만 담당하므로, 내부에서 호출하는 outbound 함수를 `monkeypatch`로 바꿔 흐름을 검증합니다.

검증 대상:
- 어떤 outbound를 호출하는지
- core 결과를 어떻게 조합하는지
- unsupported flow에서 어떤 에러를 올리는지

예시:
- `tests/test_process_source.py`

이 테스트에서는 `docflow_agent.usecases.process_source` 내부의 `load_spreadsheet_source`를 직접 바꿔 끼웁니다. 별도 port나 abstract adapter 없이도 흐름 검증이 가능합니다.

### outbound

`outbound`는 진짜 외부 시스템 대신 로컬 fake와 monkeypatch를 사용합니다.

패턴:
- HTTP 호출: `urlopen` monkeypatch
- 파일 처리: `tmp_path`
- 응답 객체: 작은 fake class 직접 작성
- automation 실행기: strategy와 결과 값 검증

예시:
- `tests/test_ecm.py`
- `tests/test_llm.py`
- `tests/test_document_automation.py`

즉 outbound는 "provider를 인터페이스로 감싸서 테스트"하는 것이 아니라 "외부 부작용을 로컬 fake로 바꿔서 테스트"합니다.

### inbound

`inbound`는 가능한 얇게 유지합니다.

- 핵심은 usecase 호출과 error translation
- business rule은 여기서 검증하지 않음
- 필요 시 framework test client로 최소 동작만 검증

이 원칙 덕분에 inbound 테스트는 적고 단순하게 유지할 수 있습니다.

## seam은 어디에 있는가

추상 interface가 없더라도 seam이 없는 것은 아닙니다.

이 프로젝트의 seam은 주로 다음 위치에 있습니다.

- usecase가 outbound 함수를 import해서 호출하는 지점
- outbound가 표준 라이브러리나 외부 라이브러리를 호출하는 지점
- settings를 읽는 지점

테스트에서는 이 seam을 `monkeypatch` 또는 fake object로 제어합니다.

## 언제 abstract adapter를 고려할 수 있는가

기본값은 도입하지 않는 것입니다. 다만 아래 조건이 생기면 검토할 수 있습니다.

- 같은 usecase가 여러 provider를 장기간 동시에 지원해야 할 때
- runtime binding이 복잡해져 테스트 setup이 지나치게 커질 때
- 동일 계약을 여러 구현체가 반복적으로 따를 때

그 전까지는 구체 모듈 + 작은 함수 + monkeypatch가 더 읽기 쉽고 유지보수에 유리합니다.
