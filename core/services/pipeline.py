from __future__ import annotations

"""전체 파이프라인 순서를 조립하는 함수 모음.

이 모듈은 크게 네 단계만 담당한다.
1. 기본 경로를 실제 파일 경로로 바꾼다.
2. URL 목록을 post_style 작업 목록으로 바꾼다.
3. main_style과 sub_style을 다시 만든다.
4. 필요하면 마지막에 글 생성까지 이어서 수행한다.
"""

from pathlib import Path

from core.models import PipelinePaths, PostStyleTask
from core.schemas.orchestrator import GenerateRequest
from core.services.generation import generate_blog_post
from core.services.naver_blog import normalize_naver_blog_url
from core.services.style_extractor import extract_main_style, extract_post_style_from_url, extract_sub_style
from core.services.source_fetcher import load_urls


def build_pipeline_paths(*, project_root: Path, urls_file: str, sources_dir: str, post_styles_dir: str, main_style_file: str, sub_style_file: str) -> PipelinePaths:
    """상대 경로 설정을 실제 파일 경로 묶음으로 바꾼다."""

    return PipelinePaths(
        project_root=project_root,
        urls_file=project_root / urls_file,
        sources_dir=project_root / sources_dir,
        post_styles_dir=project_root / post_styles_dir,
        main_style_file=project_root / main_style_file,
        sub_style_file=project_root / sub_style_file,
    )


def build_post_style_tasks(paths: PipelinePaths) -> list[PostStyleTask]:
    """URL 목록을 읽어서 post_style 추출 작업 목록으로 바꾼다."""

    tasks: list[PostStyleTask] = []
    for url in load_urls(paths.urls_file):
        _, post_id = normalize_naver_blog_url(url)
        tasks.append(
            PostStyleTask(
                url=url,
                output_file=paths.post_styles_dir / f"{post_id}.json",
                source_output_file=paths.sources_dir / f"{post_id}.txt",
            )
        )
    return tasks


def run_full_pipeline(*, paths: PipelinePaths, model: str, skip_fetch: bool = False, generation: GenerateRequest | None = None) -> dict[str, object]:
    """수집부터 생성까지 전체 흐름을 순서대로 실행한다."""

    post_style_prompt = paths.project_root / "prompts" / "post_style_extraction.txt"
    post_style_schema = paths.project_root / "schemas" / "post_style.schema.json"
    main_style_prompt = paths.project_root / "prompts" / "main_style_extraction.txt"
    main_style_schema = paths.project_root / "schemas" / "main_style.schema.json"
    sub_style_prompt = paths.project_root / "prompts" / "sub_style_extraction.txt"
    sub_style_schema = paths.project_root / "schemas" / "sub_style.schema.json"

    completed_post_ids: list[str] = []
    skipped_post_ids: list[str] = []

    # 1. 각 URL마다 source와 post_style 자산을 준비한다.
    for task in build_post_style_tasks(paths):
        post_id = task.output_file.stem
        if skip_fetch and task.source_output_file.exists() and task.output_file.exists():
            skipped_post_ids.append(post_id)
            continue

        extract_post_style_from_url(
            url=task.url,
            model=model,
            prompt_file=post_style_prompt,
            schema_file=post_style_schema,
            output_file=task.output_file,
            source_output_file=task.source_output_file,
        )
        completed_post_ids.append(post_id)

    # 2. 개별 post_style을 모아서 작성자 공통 스타일을 만든다.
    extract_main_style(
        model=model,
        prompt_file=main_style_prompt,
        schema_file=main_style_schema,
        input_dir=paths.post_styles_dir,
        output_file=paths.main_style_file,
    )

    # 3. 공통 스타일과 post_style을 같이 써서 세부 스타일 그룹을 만든다.
    extract_sub_style(
        model=model,
        prompt_file=sub_style_prompt,
        schema_file=sub_style_schema,
        input_dir=paths.post_styles_dir,
        main_style_file=paths.main_style_file,
        output_file=paths.sub_style_file,
    )

    result: dict[str, object] = {
        "model": model,
        "completed_post_ids": completed_post_ids,
        "skipped_post_ids": skipped_post_ids,
        "post_styles_dir": str(paths.post_styles_dir),
        "main_style_file": str(paths.main_style_file),
        "sub_style_file": str(paths.sub_style_file),
    }

    # 4. 요청이 있으면 바로 최종 글 생성까지 이어서 실행한다.
    if generation is not None:
        generation_request = generation.model_copy(
            update={
                "model": generation.model or model,
                "main_style_file": str(paths.main_style_file.relative_to(paths.project_root)),
                "sub_style_file": str(paths.sub_style_file.relative_to(paths.project_root)),
            }
        )
        result["generation"] = generate_blog_post(project_root=paths.project_root, request=generation_request)

    return result
