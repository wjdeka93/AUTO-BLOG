from fastapi import FastAPI

from core.schemas.orchestrator import GenerateRequest, MainStyleRebuildRequest, PipelineRunRequest, PostStyleFromUrlRequest, RunRecord, SourceFetchRequest, SubStyleRebuildRequest
from core.services.orchestrator_service import (
    fetch_sources_job,
    generate_job,
    get_pipeline_run_job,
    health_payload,
    rebuild_main_style_job,
    rebuild_sub_style_job,
    extract_post_style_job,
    run_pipeline_job,
)

app = FastAPI(title="auto-blog-orchestrator")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return health_payload()


@app.post("/sources/fetch")
def fetch_sources(payload: SourceFetchRequest) -> dict[str, object]:
    return fetch_sources_job(payload)


@app.post("/post-styles/from-url")
def post_styles_from_url(payload: PostStyleFromUrlRequest) -> dict[str, object]:
    return extract_post_style_job(payload)


@app.post("/styles/main/rebuild")
def rebuild_main_style(payload: MainStyleRebuildRequest) -> dict[str, object]:
    return rebuild_main_style_job(payload)


@app.post("/styles/sub/rebuild")
def rebuild_sub_style(payload: SubStyleRebuildRequest) -> dict[str, object]:
    return rebuild_sub_style_job(payload)


@app.post("/generate")
def generate(payload: GenerateRequest):
    return generate_job(payload)


@app.post("/pipelines/run", response_model=RunRecord)
def pipelines_run(payload: PipelineRunRequest) -> RunRecord:
    return run_pipeline_job(payload)


@app.get("/pipelines/{run_id}", response_model=RunRecord)
def get_pipeline_run(run_id: str) -> RunRecord:
    return get_pipeline_run_job(run_id)
