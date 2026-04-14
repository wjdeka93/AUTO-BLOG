# IMPLEMENTATION_NOTES

## 목적

이 문서는 지금까지 AUTO-BLOG에서 구현한 내용을 사람이 빠르게 파악할 수 있도록 정리한 문서다.
설명 방식은 다음 순서를 따른다.

1. 전체 구조
2. 서비스별 역할
3. 데이터 흐름
4. TODO 항목별 구현 대응
5. 주요 파일 설명
6. 현재 한계와 다음 확인 포인트

---

## 1. 전체 구조

현재 프로젝트는 크게 3개 런타임 요소와 1개 공통 코어로 나뉜다.

- `apps/orchestrator`
- `apps/rag`
- `postgres(pgvector)`
- `core`

의미는 이렇다.

### `apps/orchestrator`

외부에서 직접 호출하는 메인 서비스다.
이 서비스가 실제로 다음 단계를 조율한다.

- 원문 수집
- post_style 추출
- main_style 생성
- sub_style 생성
- retrieval을 포함한 글 생성
- 파이프라인 run 상태 저장/조회

즉 현재 프로젝트의 "실행 중심"은 orchestrator다.

### `apps/rag`

검색용 데이터 준비와 검색을 담당한다.
이 서비스가 하는 일은 다음과 같다.

- 원문 텍스트 청킹
- `post_style` JSON을 검색 문서로 변환
- OpenAI embedding 생성
- `pgvector`에 문서 인덱싱
- 벡터 검색 + 메타데이터 필터 검색

즉 현재 프로젝트의 "검색 중심"은 rag다.

### `postgres`

RAG 인덱스를 저장하는 벡터 저장소다.
`pgvector` 확장을 사용한다.
실제 검색 대상 문서는 `rag_documents` 테이블에 저장된다.

### `core`

서비스들이 공통으로 쓰는 비즈니스 로직이다.
예를 들면:

- 네이버 블로그 URL 정규화
- 본문 파싱
- 스타일 추출
- generation
- pipeline orchestration
- run 저장
- 로그/사용량 기록

즉 `apps/*`는 HTTP 엔드포인트이고, 실제 일은 대부분 `core/*`에서 수행한다.

---

## 2. 서비스별 역할

## 2-1. orchestrator 역할

orchestrator는 "전체 작업을 순서대로 실행하는 서비스"다.

현재 제공하는 엔드포인트는 다음과 같다.

- `GET /healthz`
- `POST /sources/fetch`
- `POST /post-styles/from-url`
- `POST /styles/main/rebuild`
- `POST /styles/sub/rebuild`
- `POST /generate`
- `POST /pipelines/run`
- `GET /pipelines/{run_id}`

각 엔드포인트 역할은 다음과 같다.

### `POST /sources/fetch`

`data/source_urls.txt` 또는 지정한 URL 파일을 읽어서 원문 본문 텍스트를 다시 수집한다.
저장 위치는 기본적으로 `data/sources/*.txt`다.

### `POST /post-styles/from-url`

URL 하나를 받아서:

- 네이버 글 본문 추출
- source text 저장
- post_style 추출
- `data/post_styles/*.json` 저장

을 수행한다.

### `POST /styles/main/rebuild`

현재 쌓여 있는 `data/post_styles/*.json` 전체를 읽어서 `main_style.json`을 다시 만든다.

### `POST /styles/sub/rebuild`

현재 쌓여 있는 `data/post_styles/*.json`과 `main_style.json`을 읽어서 `sub_style.json`을 다시 만든다.

### `POST /generate`

이미 존재하는:

- `main_style.json`
- `sub_style.json`
- retrieval 결과

를 조합해서 새 글을 생성하고 `data/outputs/*.md`에 저장한다.

### `POST /pipelines/run`

한 번에 전체 흐름을 실행한다.

흐름은 다음과 같다.

1. source 수집 또는 스킵
2. post_style 생성
3. main_style 생성
4. sub_style 생성
5. generation 요청이 있으면 글 생성까지 수행
6. run 상태를 저장

### `GET /pipelines/{run_id}`

파이프라인 실행 결과를 조회한다.
저장 파일은 `data/runs/*.json`이다.

## 2-2. rag 역할

rag는 "검색 가능한 문서를 만드는 서비스"다.

현재 엔드포인트는 다음과 같다.

- `GET /healthz`
- `POST /index/build`
- `POST /retrieval/search`

### `POST /index/build`

현재 프로젝트 파일을 읽어서 검색 인덱스를 만든다.
입력 대상은 기본적으로 다음이다.

- `data/sources/*.txt`
- `data/post_styles/*.json`

동작은 다음과 같다.

1. source text를 chunk로 분리
2. post_style JSON을 검색 문서로 변환
3. 각 문서를 embedding
4. `rag_documents` 테이블에 upsert

### `POST /retrieval/search`

질문 문장을 받아 embedding을 만들고, `rag_documents`에서 유사한 문서를 찾는다.
필터는 다음을 지원한다.

- `source_types`
- `category`
- `post_id`

---

## 3. 데이터 흐름

현재 전체 흐름은 아래처럼 연결된다.

### 1단계. 원문 수집

입력:
- `data/source_urls.txt`

출력:
- `data/sources/{post_id}.txt`

관련 파일:
- `core/services/naver_blog.py`
- `core/services/source_fetcher.py`

### 2단계. 글별 스타일 추출

입력:
- `data/sources/*.txt` 또는 URL 직접 입력
- `prompts/post_style_extraction.txt`
- `schemas/post_style.schema.json`

출력:
- `data/post_styles/{post_id}.json`

관련 파일:
- `core/services/style_extractor.py`

### 3단계. 공통 스타일 추출

입력:
- `data/post_styles/*.json`
- `prompts/main_style_extraction.txt`
- `schemas/main_style.schema.json`

출력:
- `data/styles/main_style.json`

### 4단계. 세부 스타일 추출

입력:
- `data/post_styles/*.json`
- `data/styles/main_style.json`
- `prompts/sub_style_extraction.txt`
- `schemas/sub_style.schema.json`

출력:
- `data/styles/sub_style.json`

### 5단계. RAG 인덱싱

입력:
- `data/sources/*.txt`
- `data/post_styles/*.json`

출력:
- `postgres.rag_documents`

관련 파일:
- `core/services/rag.py`

### 6단계. generation

입력:
- 생성 요청 값: topic, category, intent, audience, key_points
- `data/styles/main_style.json`
- `data/styles/sub_style.json`
- rag 검색 결과
- `prompts/blog_generation.txt`

출력:
- `data/outputs/*.md`

관련 파일:
- `core/services/generation.py`

---

## 4. TODO 항목별 구현 대응

아래는 TODO에서 각 항목이 실제 어떤 파일로 구현됐는지 연결한 것이다.

### 컨테이너 분리

구현 파일:
- `docker-compose.yml`
- `docker/Dockerfile`

설명:
- 기존 단일 컨테이너 구성을 없애고 `orchestrator`, `rag`, `postgres`로 분리했다.

### orchestrator 파이프라인 연결

구현 파일:
- `core/services/pipeline.py`
- `apps/orchestrator/main.py`

설명:
- source -> post_style -> main_style -> sub_style -> generation 흐름을 한 함수와 API로 연결했다.

### run 상태 저장

구현 파일:
- `core/services/run_store.py`

설명:
- run 생성, 완료, 실패, 조회를 JSON 파일로 저장한다.
- 저장 위치는 `data/runs`다.

### generation 구현

구현 파일:
- `core/services/generation.py`
- `prompts/blog_generation.txt`

설명:
- generation 입력을 받아 `main_style`, `sub_style`, retrieval 결과를 조합해 LLM에 전달한다.
- 결과는 markdown으로 저장한다.

### RAG 청킹/문서화/임베딩/검색

구현 파일:
- `core/services/rag.py`
- `core/schemas/rag.py`
- `apps/rag/main.py`

설명:
- source text는 chunk 단위로 저장한다.
- `post_style`은 평탄화해서 검색 문서로 저장한다.
- embedding은 OpenAI embedding 모델을 사용한다.
- 저장소는 `pgvector`다.
- retrieval API까지 붙여놨다.

### retrieval 결과를 generation 입력에 조합

구현 파일:
- `core/services/generation.py`

설명:
- `GenerateRequest.use_rag`가 true면 generation 전에 rag 검색을 수행한다.
- 검색 결과를 `retrieval_hits`로 generation payload에 넣는다.

### 로그 저장

구현 파일:
- `core/services/telemetry.py`
- `core/services/common.py`
- `apps/orchestrator/main.py`
- `apps/rag/main.py`

설명:
- 서비스 이벤트는 `data/logs/app.log`에 JSONL로 저장한다.

### OpenAI 사용량 기록

구현 파일:
- `core/services/common.py`
- `core/services/telemetry.py`

설명:
- `responses.create`, `embeddings.create` 호출마다 usage를 `data/usage/openai_usage.jsonl`에 기록한다.

### 테스트 추가

구현 파일:
- `tests/test_naver_blog.py`
- `tests/test_rag.py`
- `tests/test_openai_usage.py`
- `tests/test_api_endpoints.py`
- `tests/test_end_to_end.py`

설명:
- URL 정규화
- chunk/document 생성
- OpenAI 사용량 기록
- health endpoint
- generation + retrieval 연결

까지 확인할 수 있는 테스트 뼈대를 추가했다.

### `.env` 예시와 문서화

구현 파일:
- `.env.example`
- `README.md`

설명:
- 필요한 환경변수 예시를 추가했다.
- 요청/응답 예시와 실행법을 README에 모았다.

---

## 5. 주요 파일 설명

## `apps/orchestrator/main.py`

현재 프로젝트의 주 실행 서비스다.
실제로 외부에서 가장 많이 보게 될 파일이다.

보면 좋은 포인트:
- 어떤 API가 있는지
- 각 API가 어떤 core 함수를 부르는지
- run 상태를 어디에 저장하는지

## `apps/rag/main.py`

RAG 전용 서비스 엔드포인트다.
현재는 빌드와 검색 두 가지를 제공한다.

보면 좋은 포인트:
- 인덱싱 호출 방식
- 검색 호출 방식

## `core/services/pipeline.py`

orchestrator가 전체 단계를 어떻게 묶는지 보여준다.
가장 중요한 조율 코드다.

보면 좋은 포인트:
- source/post_style/main/sub/generation 순서
- generation이 언제 실행되는지

## `core/services/generation.py`

현재 generation 입력 조합의 핵심이다.

보면 좋은 포인트:
- sub style 선택 방식
- retrieval 결과를 어떻게 붙이는지
- output 파일명을 어떻게 정하는지

## `core/services/rag.py`

현재 검색 계층의 중심이다.

보면 좋은 포인트:
- source를 어떻게 chunk로 나누는지
- post_style을 어떻게 검색 문서로 바꾸는지
- `pgvector`에 어떻게 저장하는지
- 검색 SQL이 어떻게 구성되는지

## `core/services/common.py`

OpenAI 호출 래퍼와 사용량 기록이 들어 있다.
공통 운영 포인트는 여기서 보는 게 가장 빠르다.

## `core/services/telemetry.py`

서비스 이벤트 로그와 usage 로그를 파일에 적는 로직이 들어 있다.

---

## 6. 현재 한계

완료된 것과 별개로, 지금 상태에서 알고 있어야 할 한계도 있다.

### 1. 테스트 실행 자체는 아직 환경 의존

테스트 파일은 만들었지만, 실제 `pytest` 실행은 현재 세션 환경에 `pytest`가 없어서 바로 돌리진 못했다.
즉 "테스트 코드 작성"은 끝났고 "실제 실행 검증"은 환경 준비가 더 필요하다.

### 2. retrieval 품질은 아직 튜닝 전

현재 retrieval은 기본적인 벡터 검색 + 메타데이터 필터 수준이다.
문서 가중치, reranking, chunk 전략 튜닝은 아직 하지 않았다.

### 3. generation 품질은 프롬프트 의존

현재 generation은 구조상 연결은 끝났지만, 결과 품질은 프롬프트와 retrieval 품질에 직접 영향을 받는다.
즉 이후 품질 조정은 충분히 있을 수 있다.

### 4. 비용 계산은 usage 기록까지

현재는 usage를 기록하지만, 금액 환산까지는 하지 않는다.
즉 "비용 로그 기반 계산"은 나중에 붙일 수 있지만 아직은 토큰 기록 중심이다.

---

## 7. 다음에 보면 좋은 순서

처음부터 파일을 다 읽기보다 아래 순서가 가장 이해가 쉽다.

1. `README.md`
2. `TODO.md`
3. `apps/orchestrator/main.py`
4. `core/services/pipeline.py`
5. `core/services/generation.py`
6. `apps/rag/main.py`
7. `core/services/rag.py`
8. `SESSION_SUMMARY.md`

---

## 8. 한 줄 요약

현재 AUTO-BLOG는:

- 스타일 추출 파이프라인이 있고
- RAG 인덱싱/검색이 있고
- generation이 retrieval 결과까지 받아서 동작하며
- 로그/usage 기록과 테스트 뼈대까지 갖춘 상태다.

즉 "기능 연결"은 끝났고, 앞으로는 주로 품질 검증과 운영 검증 단계로 보면 된다.
