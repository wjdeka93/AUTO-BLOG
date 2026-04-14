from __future__ import annotations

"""Pipeline assembly helpers.

The orchestrator uses this module to translate a few top-level path settings into a
repeatable end-to-end sequence:

1. build file paths
2. derive per-post extraction tasks from the URL list
3. rebuild main/sub style assets
4. optionally generate the final blog post
"""

from pathlib import Path

from core.models import PipelinePaths, PostStyleTask
from core.schemas.orchestrator import GenerateRequest
from core.services.generation import generate_blog_post
from core.services.naver_blog import normalize_naver_blog_url
from core.services.style_extractor import extract_main_style, extract_post_style_from_url, extract_sub_style
from core.services.source_fetcher import load_urls


def build_pipeline_paths(*, project_root: Path, urls_file: str, sources_dir: str, post_styles_dir: str, main_style_file: str, sub_style_file: str) -> PipelinePaths:
    """Expand project-relative pipeline settings into concrete filesystem paths."""

    return PipelinePaths(
        project_root=project_root,
        urls_file=project_root / urls_file,
        sources_dir=project_root / sources_dir,
        post_styles_dir=project_root / post_styles_dir,
        main_style_file=project_root / main_style_file,
        sub_style_file=project_root / sub_style_file,
    )


def build_post_style_tasks(paths: PipelinePaths) -> list[PostStyleTask]:
    """Turn the URL list into deterministic extraction tasks.

    Each task knows both output destinations up front:
    - raw source text file
    - structured post_style JSON file
    """

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
    """Run the full content-preparation pipeline.

    The extraction prompts and schemas are fixed project assets, so we resolve them
    once here and then execute the steps in order. When `skip_fetch` is enabled we
    reuse existing source/post_style files if both are already present for a post.
    """

    post_style_prompt = paths.project_root / "prompts" / "post_style_extraction.txt"
    post_style_schema = paths.project_root / "schemas" / "post_style.schema.json"
    main_style_prompt = paths.project_root / "prompts" / "main_style_extraction.txt"
    main_style_schema = paths.project_root / "schemas" / "main_style.schema.json"
    sub_style_prompt = paths.project_root / "prompts" / "sub_style_extraction.txt"
    sub_style_schema = paths.project_root / "schemas" / "sub_style.schema.json"

    completed_post_ids: list[str] = []
    skipped_post_ids: list[str] = []

    # Step 1: make sure every URL has a matching source text and post_style asset.
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

    # Step 2: summarize all individual post styles into a single author-wide style.
    extract_main_style(
        model=model,
        prompt_file=main_style_prompt,
        schema_file=main_style_schema,
        input_dir=paths.post_styles_dir,
        output_file=paths.main_style_file,
    )

    # Step 3: derive category/group-specific sub styles from the same post_style set.
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

    # Step 4: optionally continue straight into final post generation.
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
