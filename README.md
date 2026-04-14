# AUTO-BLOG

네이버 블로그 글을 수집하고, 스타일 자산을 추출한 뒤, 그 스타일과 retrieval 결과를 바탕으로 새 글을 생성하는 프로젝트입니다.

## 디렉터리

- `apps/`: HTTP 엔드포인트만 두는 런타임 레이어
- `core/`: 실제 비즈니스 로직과 공통 유틸
- `prompts/`: OpenAI 프롬프트
- `schemas/`: JSON 스키마
- `scripts/`: 수동 실행용 CLI
- `data/`: 소스, 스타일 자산, 생성 결과, run/로그/usage 저장
- `docker/`: Docker 정의
- `tests/`: 테스트

## 읽는 순서

1. `apps/orchestrator/main.py`
2. `core/services/orchestrator_service.py`
3. `core/services/pipeline.py`
4. `core/services/generation.py`
5. `apps/rag/main.py`
6. `core/services/rag_service.py`
7. `core/services/rag.py`

## 구조 원칙

- `apps/*/main.py`는 가능한 얇게 유지한다.
- 엔드포인트가 호출하는 실제 일은 `core/services/*`로 모은다.
- 경로 계산은 `core/runtime.py`를 기준으로 한다.
- source와 post_style은 생성 시점에 파일 저장과 RAG 적재를 동시에 수행한다.
