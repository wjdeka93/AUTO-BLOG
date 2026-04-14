# AUTO-BLOG

네이버 블로그 글을 수집하고, 스타일 자산을 추출한 뒤, 그 스타일과 retrieval 결과를 바탕으로 새 글을 생성하는 프로젝트입니다.

## 디렉터리

- `apps/`: FastAPI 진입점
- `core/`: 실제 비즈니스 로직
- `prompts/`: OpenAI 프롬프트
- `schemas/`: JSON 스키마
- `scripts/`: 수동 실행용 CLI
- `data/`: 원문, 스타일 자산, 생성 결과
- `docker/`: Docker 설정
- `tests/`: 테스트

## 먼저 볼 파일

1. `apps/orchestrator/main.py`
2. `core/services/orchestrator_service.py`
3. `core/services/pipeline.py`
4. `core/services/generation.py`
5. `apps/rag/main.py`
6. `core/services/rag.py`

## 구조 원칙

- API 파일은 가능한 얇게 유지한다.
- 실제 작업은 `core/services`에 모은다.
- source와 post_style은 저장할 때 바로 RAG에도 반영한다.
- RAG 저장소는 `postgres + pgvector`를 사용한다.
