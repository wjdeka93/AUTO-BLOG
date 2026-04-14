from __future__ import annotations

"""Final blog-post generation service.

This module is responsible for the last step of the system: turning the user request,
the extracted style assets, and optional RAG retrieval hits into a markdown blog post.
"""

import json
import re
from pathlib import Path
from typing import Any

from core.schemas.orchestrator import GenerateRequest
from core.schemas.rag import SearchRequest
from core.services.common import build_openai_client, create_response, load_json, load_text
from core.services.rag import search_documents


def slugify_filename(value: str) -> str:
    """Create a filesystem-safe output filename from category/topic text."""

    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9°¡-ÆR]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "generated-post"


def select_sub_style(sub_style: dict[str, Any], *, category: str, sub_style_group: str | None) -> dict[str, Any] | None:
    """Pick the most relevant sub-style block for the requested category.

    Matching priority is:
    1. explicit `sub_style_group` from the request
    2. exact match against the requested category
    3. loose match against `when_to_use`
    4. first available group as a fallback
    """

    grouped_styles = sub_style.get("grouped_styles", [])
    if not isinstance(grouped_styles, list):
        return None

    if sub_style_group:
        for group in grouped_styles:
            if str(group.get("group_name", "")).lower() == sub_style_group.lower():
                return group

    for group in grouped_styles:
        if str(group.get("group_name", "")).lower() == category.lower():
            return group

    for group in grouped_styles:
        when_to_use = str(group.get("when_to_use", ""))
        if category.lower() in when_to_use.lower():
            return group

    return grouped_styles[0] if grouped_styles else None


def build_generation_query(request: GenerateRequest) -> str:
    """Build the semantic-search query used for RAG retrieval.

    We combine the topic, category, intent, audience, and key points so retrieval uses
    the same context that the generation model will see later.
    """

    parts = [request.topic, request.category, request.intent, request.audience, *request.key_points]
    return "\n".join(part for part in parts if part)


def retrieve_context(request: GenerateRequest) -> list[dict[str, Any]]:
    """Fetch relevant reference documents from the vector index when enabled.

    Retrieval is intentionally soft-failing here. If the RAG service or database is not
    available, we still allow generation to continue with style assets only.
    """

    if not request.use_rag:
        return []

    try:
        hits = search_documents(
            request=SearchRequest(
                query=build_generation_query(request),
                limit=request.retrieval_limit,
                source_types=request.retrieval_source_types,
                category=request.category,
            )
        )
        return [hit.model_dump() for hit in hits]
    except Exception:
        return []


def build_generation_payload(
    *,
    request: GenerateRequest,
    main_style: dict[str, Any],
    selected_sub_style: dict[str, Any] | None,
    retrieval_hits: list[dict[str, Any]],
) -> str:
    """Serialize all generation inputs into one structured JSON payload for the model."""

    payload = {
        "request": request.model_dump(),
        "main_style": main_style,
        "selected_sub_style": selected_sub_style,
        "retrieval_hits": retrieval_hits,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def generate_blog_post(*, project_root: Path, request: GenerateRequest) -> dict[str, Any]:
    """Generate and persist one markdown blog post.

    Input assembly happens in four stages:
    1. load prompt and style assets
    2. choose the best matching sub-style
    3. optionally retrieve supporting context from RAG
    4. call OpenAI and save the markdown result
    """

    client = build_openai_client()
    prompt = load_text(project_root / request.prompt_file)
    main_style = load_json(project_root / request.main_style_file)
    sub_style = load_json(project_root / request.sub_style_file)
    selected_sub_style = select_sub_style(
        sub_style,
        category=request.category,
        sub_style_group=request.sub_style_group,
    )
    retrieval_hits = retrieve_context(request)

    response = create_response(
        client=client,
        model=request.model,
        input=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": build_generation_payload(
                    request=request,
                    main_style=main_style,
                    selected_sub_style=selected_sub_style,
                    retrieval_hits=retrieval_hits,
                ),
            },
        ],
        metadata={
            "operation": "generate_blog_post",
            "category": request.category,
            "topic": request.topic,
            "retrieval_count": len(retrieval_hits),
        },
    )
    markdown = response.output_text.strip()

    output_path = project_root / (
        request.output_file
        or f"data/outputs/{slugify_filename(request.category + '-' + request.topic)}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown + "\n", encoding="utf-8")

    return {
        "output_file": str(output_path),
        "selected_sub_style_group": selected_sub_style.get("group_name") if selected_sub_style else None,
        "retrieval_count": len(retrieval_hits),
        "retrieval_hits": retrieval_hits,
        "markdown": markdown,
    }
