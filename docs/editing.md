# Edit Intent And Automation

이 프로젝트에서 문서 수정은 `core`와 `outbound` 사이의 역할 분리가 가장 중요합니다.

## 기본 원칙

- `core/edit`는 무엇을 바꿔야 하는지 결정한다
- `outbound`는 그 변경을 실제 파일이나 애플리케이션에 적용한다
- `usecases`는 edit intent 생성과 실행 시점을 오케스트레이션한다

즉, core는 `CellValueEditIntent`, `InsertSheetEditIntent`, `RecalculateWorkbookEditIntent`, `SaveDocumentEditIntent` 같은 구조화된 edit intent를 만들고, outbound는 이를 openpyxl, Excel COM, 또는 RPA로 실행합니다.

## 실행 전략

기본 실행 전략은 다음과 같습니다.

1. 가능하면 파일 레벨 처리부터 시도한다
2. 파일 레벨 처리로 해결되지 않으면 애플리케이션 자동화를 사용한다
3. 어떤 전략을 택할지는 outbound가 결정한다

## outbound 책임

- 파일 라이브러리 사용
- Excel 애플리케이션 세션 시작/재사용/종료
- COM 또는 RPA 실행
- 파일 잠금 처리
- 저장과 재계산 보장
- 필요 시 read-back 검증

## 금지 사항

- core가 openpyxl, COM, RPA 라이브러리를 import 하면 안 된다
- usecase가 workbook, worksheet, COM 객체를 다루면 안 된다
- outbound 밖으로 UI automation object가 나오면 안 된다

## 테스트 전략

- edit intent 생성은 unit test로 검증
- 파일 수정기는 integration test로 검증
- RPA/COM 연동 테스트는 환경 의존적일 수 있으므로 optional test로 분리 가능
