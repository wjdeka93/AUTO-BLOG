from __future__ import annotations

"""오케스트레이터가 호출하는 실제 작업 모음.

`apps/orchestrator/main.py`는 라우팅만 맡고,
여기서는 요청을 받아 실제 수집, 스타일 추출, 파이프라인 실행을 처리한다.
"""

from typing import Any

from fastapi import HTTPException

from core.runtime import PROJECT_ROOT, resolve_project_path
from core.schemas.orchestrator import (
    GenerateRequest,
    MainStyleRebuildRequest,
    PipelineRunRequest,
    PostStyleFromUrlRequest,
    RunRecord,
    SourceFetchRequest,
    SubStyleRebuildRequest,
)
from core.services.common import log_event
from core.services.generation import generate_blog_post
from core.services.naver_blog import normalize_naver_blog_url
from core.services.pipeline import build_pipeline_paths, run_full_pipeline
from core.services.run_store import RunStore
from core.services.source_fetcher import fetch_all_sources
from core.services.style_extractor import extract_main_style, extract_post_style_from_url, extract_sub_style

# 파이프라인 실행 이력은 파일로 남겨서 나중에 run_id로 다시 조회할 수 있게 한다.
run_store = RunStore(PROJECT_ROOT / "data" / "runs")


def health_payload() -> dict[str, str]:
    """오케스트레이터 상태 확인용 응답이다."""

    return {"service": "orchestrator", "status": "ok"}


def fetch_sources_job(payload: SourceFetchRequest) -> dict[str, object]:
    """URL 목록을 읽어서 원문 텍스트 파일을 만든다."""

    posts = fetch_all_sources(resolve_project_path(payload.urls_file), resolve_project_path(payload.output_dir))
    result = {
        "count": len(posts),
        "post_ids": [post.metadata["post_id"] for post in posts],
        "output_dir": str(resolve_project_path(payload.output_dir)),
    }
    log_event(service="orchestrator", event="sources.fetch", payload=result)
    return result


def extract_post_style_job(payload: PostStyleFromUrlRequest) -> dict[str, object]:
    """URL 하나를 받아 source와 post_style을 함께 만든다.

    출력 경로를 따로 주지 않으면 URL에서 뽑은 post_id를 파일명으로 사용한다.
    """

    _, post_id = normalize_naver_blog_url(payload.url)
    output_file = resolve_project_path(payload.output_file or f"data/post_styles/{post_id}.json")
    source_output_file = resolve_project_path(payload.source_output_file or f"data/sources/{post_id}.txt")
    result = extract_post_style_from_url(
        url=payload.url,
        model=payload.model,
        prompt_file=resolve_project_path(payload.prompt_file),
        schema_file=resolve_project_path(payload.schema_file),
        output_file=output_file,
        source_output_file=source_output_file,
    )
    response = {
        "post_id": result.get("post_id", post_id),
        "output_file": str(output_file),
        "source_output_file": str(source_output_file),
    }
    log_event(service="orchestrator", event="post_styles.from_url", payload=response)
    return response


def rebuild_main_style_job(payload: MainStyleRebuildRequest) -> dict[str, object]:
    """저장된 post_style 전체를 기준으로 main_style을 다시 만든다."""

    result = extract_main_style(
        model=payload.model,
        prompt_file=resolve_project_path(payload.prompt_file),
        schema_file=resolve_project_path(payload.schema_file),
        input_dir=resolve_project_path(payload.input_dir),
        output_file=resolve_project_path(payload.output_file),
    )
    response = {
        "author": result.get("author", ""),
        "output_file": str(resolve_project_path(payload.output_file)),
    }
    log_event(service="orchestrator", event="styles.main.rebuild", payload=response)
    return response


def rebuild_sub_style_job(payload: SubStyleRebuildRequest) -> dict[str, object]:
    """main_style과 post_style을 이용해 세부 그룹 스타일을 다시 만든다."""

    result = extract_sub_style(
        model=payload.model,
        prompt_file=resolve_project_path(payload.prompt_file),
        schema_file=resolve_project_path(payload.schema_file),
        input_dir=resolve_project_path(payload.input_dir),
        main_style_file=resolve_project_path(payload.main_style_file),
        output_file=resolve_project_path(payload.output_file),
    )
    response = {
        "author": result.get("author", ""),
        "output_file": str(resolve_project_path(payload.output_file)),
    }
    log_event(service="orchestrator", event="styles.sub.rebuild", payload=response)
    return response


def generate_job(payload: GenerateRequest) -> dict[str, Any]:
    """스타일 자산과 retrieval 결과를 합쳐 최종 글을 생성한다."""

    result = generate_blog_post(project_root=PROJECT_ROOT, request=payload)
    log_event(
        service="orchestrator",
        event="generate",
        payload={"output_file": result["output_file"], "retrieval_count": result["retrieval_count"]},
    )
    return result


def run_pipeline_job(payload: PipelineRunRequest) -> RunRecord:
    """전체 파이프라인을 한 번에 실행하고 실행 기록을 남긴다."""

    run = run_store.create(run_type="pipeline", payload=payload.model_dump())
    try:
        paths = build_pipeline_paths(
            project_root=PROJECT_ROOT,
            urls_file=payload.paths.urls_file,
            sources_dir=payload.paths.sources_dir,
            post_styles_dir=payload.paths.post_styles_dir,
            main_style_file=payload.paths.main_style_file,
            sub_style_file=payload.paths.sub_style_file,
        )
        output = run_full_pipeline(
            paths=paths,
            model=payload.model,
            skip_fetch=payload.skip_fetch,
            generation=payload.generation,
        )
        completed = run_store.complete(run, output=output)
        log_event(service="orchestrator", event="pipeline.run", payload={"run_id": completed.run_id, "status": completed.status})
        return completed
    except Exception as exc:
        failed = run_store.fail(run, error=str(exc))
        log_event(service="orchestrator", event="pipeline.run.failed", payload={"run_id": failed.run_id, "error": failed.error})
        return failed


def get_pipeline_run_job(run_id: str) -> RunRecord:
    """저장된 파이프라인 실행 결과를 다시 읽어온다."""

    try:
        result = run_store.get(run_id)
        log_event(service="orchestrator", event="pipeline.get", payload={"run_id": run_id})
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
