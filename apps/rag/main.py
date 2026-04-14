from fastapi import FastAPI

from core.schemas.rag import BuildIndexRequest, SearchRequest
from core.services.rag_service import build_index_job, health_payload, retrieval_search_job

app = FastAPI(title="auto-blog-rag")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return health_payload()


@app.post("/index/build")
def index_build(payload: BuildIndexRequest):
    return build_index_job(payload)


@app.post("/retrieval/search")
def retrieval_search(payload: SearchRequest):
    return retrieval_search_job(payload)
