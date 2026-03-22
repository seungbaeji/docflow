# docflow-agent docs

이 문서는 `docflow-agent`의 source/unit/bundle 아키텍처와 outbound 가이드를 정리합니다.

## 아키텍처

프로젝트는 아래 의존 흐름을 기준으로 확장합니다.

```text
inbound -> usecases
usecases -> core
usecases -> outbound
```

데이터 흐름은 다음 개념을 사용합니다.

```text
source -> parse -> unit -> category -> combine -> analyze -> rules
```

- `source`: 입력 원천
- `unit`: 처리 단위
- `bundle`: 분석 전 결합 결과
- `category`: business meaning

## 현재 문서

- `model.md`: source, unit, bundle, category 모델 설명
- `ecm.md`: 범용 ECM 연동 방식과 `crypto/search/download/upload` 설명
- `llm.md`: Agent에서 사용하는 LLM outbound 구성과 설정 설명
