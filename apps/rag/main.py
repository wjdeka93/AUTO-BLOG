from fastapi import FastAPI

from core.runtime import PROJECT_ROOT
from core.schemas.rag import BuildIndexRequest, SearchRequest
from core.services.common import log_event
from core.services.rag import build_index, search_documents

app = FastAPI(title="auto-blog-rag")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """RAG 서비스 상태만 간단히 확인한다."""

    return {"service": "rag", "status": "ok"}


@app.post("/index/build")
def index_build(payload: BuildIndexRequest) -> dict[str, object]:
    """저장된 source와 post_style 파일을 기준으로 전체 인덱스를 다시 만든다."""

    result = build_index(project_root=PROJECT_ROOT, request=payload)
    log_event(service="rag", event="index.build", payload=result)
    return result


@app.post("/retrieval/search")
def retrieval_search(payload: SearchRequest) -> dict[str, object]:
    """벡터 검색 결과를 API 응답 형식으로 감싸서 돌려준다."""

    hits = search_documents(request=payload)
    result = {
        "count": len(hits),
        "hits": [hit.model_dump() for hit in hits],
    }
    log_event(service="rag", event="retrieval.search", payload={"query": payload.query, "count": result["count"]})
    return result
