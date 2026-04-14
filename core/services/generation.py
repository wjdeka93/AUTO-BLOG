from __future__ import annotations

"""스타일 자산과 검색 결과를 이용해 최종 글을 만드는 모듈."""

import json
import re
from pathlib import Path
from typing import Any

from core.schemas.orchestrator import GenerateRequest
from core.schemas.rag import SearchRequest
from core.services.common import build_openai_client, create_response, load_json, load_text
from core.services.rag import search_documents


def slugify_filename(value: str) -> str:
    """카테고리와 주제를 파일명으로 안전하게 바꾼다."""

    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9가-힣]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "generated-post"


def select_sub_style(sub_style: dict[str, Any], *, category: str, sub_style_group: str | None) -> dict[str, Any] | None:
    """요청 카테고리에 가장 잘 맞는 sub_style 그룹을 고른다.

    우선순위는 다음과 같다.
    1. 요청에서 sub_style_group을 직접 지정한 경우
    2. category와 group_name이 정확히 일치하는 경우
    3. when_to_use 설명 안에 category가 들어 있는 경우
    4. 아무것도 없으면 첫 번째 그룹
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
    """RAG 검색에 쓸 질의 문자열을 만든다."""

    parts = [request.topic, request.category, request.intent, request.audience, *request.key_points]
    return "\n".join(part for part in parts if part)


def retrieve_context(request: GenerateRequest) -> list[dict[str, Any]]:
    """필요하면 벡터 검색으로 참고 문서를 가져온다.

    검색 계층에 문제가 생겨도 생성 자체는 계속할 수 있게 예외는 빈 결과로 처리한다.
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
    """생성 모델에 넘길 입력을 하나의 JSON 문자열로 묶는다."""

    payload = {
        "request": request.model_dump(),
        "main_style": main_style,
        "selected_sub_style": selected_sub_style,
        "retrieval_hits": retrieval_hits,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def generate_blog_post(*, project_root: Path, request: GenerateRequest) -> dict[str, Any]:
    """최종 마크다운 글을 생성하고 파일로 저장한다.

    흐름은 단순하다.
    1. 프롬프트와 스타일 자산을 읽는다.
    2. 알맞은 sub_style을 고른다.
    3. 필요하면 retrieval 결과를 붙인다.
    4. OpenAI 호출 후 마크다운 파일로 저장한다.
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
