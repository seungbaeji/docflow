# Edit Intent And Automation

이 프로젝트에서 문서 수정은 `core`와 `outbound` 사이의 역할 분리가 가장 중요합니다.

## 기본 원칙

- `core/edit`는 무엇을 바꿔야 하는지 결정한다
- `outbound`는 그 변경을 실제 파일이나 애플리케이션에 적용한다
- `usecases`는 edit intent 생성과 실행 시점을 오케스트레이션한다

즉, core는 구조화된 edit intent를 만들고, outbound는 이를 실제 파일 처리나 애플리케이션 자동화로 실행합니다.

구체적인 실행 전략과 adapter 선택은 bootstrap과 outbound 구현이 담당합니다.

## 금지 사항

- core가 openpyxl, COM, RPA 라이브러리를 import 하면 안 된다
- usecase가 workbook, worksheet, COM 객체를 다루면 안 된다
- outbound 밖으로 UI automation object가 나오면 안 된다

## 테스트 전략

- edit intent 자체는 value object / workflow 결과 기준으로 검증
- 실제 실행기는 external adapter가 생긴 뒤 integration test로 검증
