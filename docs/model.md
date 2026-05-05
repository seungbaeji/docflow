# Source / Unit / Bundle model

이 프로젝트는 파일 중심 시스템이 아니라 source 중심 시스템입니다.

## 핵심 개념

- `source`: 입력 원천. ECM, mail, SAP/API 등
- `unit`: source를 파싱한 뒤 얻는 처리 단위
- `category`: unit 또는 bundle의 business meaning
- `bundle`: 여러 unit을 비즈니스 목적에 맞게 합친 구조
- `edit intent`: 수정이 필요할 때 core가 만드는 구조화된 변경 명세

## 설계 원칙

- usecase가 core와 outbound를 오케스트레이션한다
- core는 구조화된 타입만 다룬다
- outbound는 파일, bytes, 외부 API, DB 응답, 문서 수정 실행을 다룬다
- 타입은 추상 base model이 아니라 실제 데이터 구조를 반영한다

## value / boundary

- `types/value`: 내부 value object
- `types/boundary`: 외부 입력/출력 DTO
- 외부 입력은 boundary에서 검증한 뒤 value object로 변환한다
