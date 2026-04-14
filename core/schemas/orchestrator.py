from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PipelinePathsPayload(BaseModel):
    urls_file: str = "data/source_urls.txt"
    sources_dir: str = "data/sources"
    post_styles_dir: str = "data/post_styles"
    main_style_file: str = "data/styles/main_style.json"
    sub_style_file: str = "data/styles/sub_style.json"
    outputs_dir: str = "data/outputs"


class GenerateRequest(BaseModel):
    topic: str
    category: str
    intent: str
    audience: str
    key_points: list[str] = Field(default_factory=list)
    sub_style_group: str | None = None
    output_file: str | None = None
    model: str = "gpt-5"
    prompt_file: str = "prompts/blog_generation.txt"
    main_style_file: str = "data/styles/main_style.json"
    sub_style_file: str = "data/styles/sub_style.json"
    use_rag: bool = True
    retrieval_limit: int = 5
    retrieval_source_types: list[str] = Field(default_factory=lambda: ["source_chunk", "post_style"])


class PipelineRunRequest(BaseModel):
    model: str = "gpt-5"
    skip_fetch: bool = False
    paths: PipelinePathsPayload = Field(default_factory=PipelinePathsPayload)
    generation: GenerateRequest | None = None


class SourceFetchRequest(BaseModel):
    urls_file: str = "data/source_urls.txt"
    output_dir: str = "data/sources"


class PostStyleFromUrlRequest(BaseModel):
    url: str
    model: str = "gpt-5"
    output_file: str | None = None
    source_output_file: str | None = None
    prompt_file: str = "prompts/post_style_extraction.txt"
    schema_file: str = "schemas/post_style.schema.json"


class MainStyleRebuildRequest(BaseModel):
    input_dir: str = "data/post_styles"
    output_file: str = "data/styles/main_style.json"
    prompt_file: str = "prompts/main_style_extraction.txt"
    schema_file: str = "schemas/main_style.schema.json"
    model: str = "gpt-5"


class SubStyleRebuildRequest(BaseModel):
    input_dir: str = "data/post_styles"
    main_style_file: str = "data/styles/main_style.json"
    output_file: str = "data/styles/sub_style.json"
    prompt_file: str = "prompts/sub_style_extraction.txt"
    schema_file: str = "schemas/sub_style.schema.json"
    model: str = "gpt-5"


class RunRecord(BaseModel):
    run_id: str
    run_type: str
    status: str
    started_at: str
    finished_at: str | None = None
    input: dict[str, Any]
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
