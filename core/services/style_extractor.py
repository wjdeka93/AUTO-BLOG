from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.models import SourcePost
from core.services.common import (
    build_openai_client,
    create_response,
    load_json,
    load_text,
    save_json,
    schema_name_from_path,
)
from core.services.naver_blog import fetch_naver_post
from core.services.rag import sync_post_style_payload, sync_source_post


def build_user_payload(metadata: dict[str, Any], post_text: str) -> str:
    return json.dumps({"metadata": metadata, "post_text": post_text}, ensure_ascii=False, indent=2)


def run_schema_prompt(model: str, prompt_file: Path, schema_file: Path, user_payload: str, fallback_name: str) -> dict[str, Any]:
    client = build_openai_client()
    prompt = load_text(prompt_file)
    schema = load_json(schema_file)
    schema_name = schema_name_from_path(schema_file, fallback_name)

    response = create_response(
        client=client,
        model=model,
        input=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_payload},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
        metadata={
            "fallback_name": fallback_name,
            "prompt_file": str(prompt_file),
            "schema_file": str(schema_file),
        },
    )
    return json.loads(response.output_text)


def extract_post_style_from_source(*, model: str, prompt_file: Path, schema_file: Path, source_post: SourcePost) -> dict[str, Any]:
    user_payload = build_user_payload(source_post.metadata, source_post.post_text)
    return run_schema_prompt(model, prompt_file, schema_file, user_payload, "post_style")


def extract_post_style_from_url(*, url: str, model: str, prompt_file: Path, schema_file: Path, output_file: Path, source_output_file: Path) -> dict[str, Any]:
    source_post = fetch_naver_post(url)
    source_output_file.parent.mkdir(parents=True, exist_ok=True)
    source_output_file.write_text(source_post.post_text, encoding="utf-8")
    sync_source_post(source_post)
    result = extract_post_style_from_source(
        model=model,
        prompt_file=prompt_file,
        schema_file=schema_file,
        source_post=source_post,
    )
    save_json(output_file, result)
    sync_post_style_payload(result)
    return result


def extract_post_style_from_file(*, model: str, prompt_file: Path, schema_file: Path, input_file: Path, output_file: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    source_post = SourcePost(metadata=metadata, post_text=load_text(input_file))
    sync_source_post(source_post)
    result = extract_post_style_from_source(
        model=model,
        prompt_file=prompt_file,
        schema_file=schema_file,
        source_post=source_post,
    )
    save_json(output_file, result)
    sync_post_style_payload(result)
    return result


def load_post_styles(input_dir: Path) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob("*.json")):
        posts.append(load_json(path))
    if not posts:
        raise ValueError(f"post_style JSON이 없습니다: {input_dir}")
    return posts


def extract_main_style(*, model: str, prompt_file: Path, schema_file: Path, input_dir: Path, output_file: Path) -> dict[str, Any]:
    post_styles = load_post_styles(input_dir)
    user_payload = json.dumps({"post_styles": post_styles}, ensure_ascii=False, indent=2)
    result = run_schema_prompt(model, prompt_file, schema_file, user_payload, "main_style")
    save_json(output_file, result)
    return result


def extract_sub_style(*, model: str, prompt_file: Path, schema_file: Path, input_dir: Path, main_style_file: Path, output_file: Path) -> dict[str, Any]:
    post_styles = load_post_styles(input_dir)
    main_style = load_json(main_style_file)
    user_payload = json.dumps({"main_style": main_style, "post_styles": post_styles}, ensure_ascii=False, indent=2)
    result = run_schema_prompt(model, prompt_file, schema_file, user_payload, "sub_style")
    save_json(output_file, result)
    return result
