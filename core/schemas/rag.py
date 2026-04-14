from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BuildIndexRequest(BaseModel):
    sources_dir: str = "data/sources"
    post_styles_dir: str = "data/post_styles"
    embedding_model: str = "text-embedding-3-small"
    recreate: bool = False
    chunk_size: int = 1200
    chunk_overlap: int = 150


class SearchRequest(BaseModel):
    query: str
    embedding_model: str = "text-embedding-3-small"
    limit: int = 5
    source_types: list[str] = Field(default_factory=list)
    category: str | None = None
    post_id: str | None = None


class IndexedDocument(BaseModel):
    doc_id: str
    post_id: str
    source_type: str
    title: str | None = None
    category: str | None = None
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchHit(BaseModel):
    doc_id: str
    post_id: str
    source_type: str
    category: str | None = None
    title: str | None = None
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    distance: float
