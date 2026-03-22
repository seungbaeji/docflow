# Source / Unit / Bundle model

이 프로젝트는 파일 중심 시스템이 아니라 source 중심 시스템입니다.

## 핵심 개념

- `source`: 입력 원천. ECM, mail, SAP/API 등
- `unit`: source를 파싱한 뒤 얻는 처리 단위
- `category`: unit 또는 bundle의 business meaning
- `bundle`: 여러 unit을 비즈니스 목적에 맞게 합친 구조
- `edit intent`: 수정이 필요할 때 core가 만드는 구조화된 변경 명세

## 예시

- Excel source -> sheet unit -> invoice category -> `InvoiceBundle`
- PDF source -> page group unit -> settlement category -> `SettlementBundle`
- SAP/API source -> record unit -> reconciliation category -> matching bundle
- Invoice bundle -> edit intent -> outbound execution

## 설계 원칙

- usecase가 core와 outbound를 오케스트레이션한다
- core는 구조화된 타입만 다룬다
- outbound는 파일, bytes, 외부 API, DB 응답, 문서 수정 실행을 다룬다
- 타입은 추상 base model이 아니라 실제 데이터 구조를 반영한다

## editing 원칙

- core는 수정 실행이 아니라 수정 의도를 표현한다
- usecase는 edit intent 생성과 실행 시점을 오케스트레이션한다
- outbound는 파일 처리 또는 애플리케이션 자동화로 edit intent를 적용한다
- Excel workbook, worksheet, COM object, UI automation object는 outbound 밖으로 노출하지 않는다
