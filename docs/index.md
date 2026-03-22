# docflow-agent docs

이 문서는 `docflow-agent`의 source/unit/bundle 아키텍처와 edit-intent 기반 문서 수정, 그리고 outbound 실행 가이드를 정리합니다.

이 문서들은 `mkdocs.yml` 기준으로 사이트로 빌드되며, GitHub Pages에 배포할 수 있습니다.

## 아키텍처

프로젝트는 아래 의존 흐름을 기준으로 확장합니다.

```text
inbound -> usecases
usecases -> core
usecases -> outbound
```

데이터 흐름은 다음 개념을 사용합니다.

```text
source -> parse -> unit -> category -> combine -> analyze -> rules -> edit
```

- `source`: 입력 원천
- `unit`: 처리 단위
- `bundle`: 분석 전 결합 결과
- `category`: business meaning
- `edit`: core가 만든 수정 명세. 실제 적용은 outbound에서 실행

## 현재 문서

- `model.md`: source, unit, bundle, category 모델 설명
- `editing.md`: edit intent와 document automation 경계 설명
- `ecm.md`: 범용 ECM 연동 방식과 `crypto/search/download/upload` 설명
- `llm.md`: Agent에서 사용하는 LLM outbound 구성과 설정 설명
