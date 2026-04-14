from __future__ import annotations

"""RAG indexing and retrieval helpers.

This module owns the data path between local project assets and pgvector:

- raw source text -> source chunks -> embeddings -> `rag_documents`
- post_style JSON -> flattened text document -> embeddings -> `rag_documents`
- user query -> query embedding -> nearest-neighbor search

The rest of the project can treat this module as the single place that knows how to
shape documents for retrieval and how to talk to Postgres/pgvector.
"""

import json
import os
from pathlib import Path
from typing import Any

import psycopg

from core.models import SourcePost
from core.schemas.rag import BuildIndexRequest, IndexedDocument, SearchHit, SearchRequest
from core.services.common import build_openai_client, create_embeddings, load_json, load_text, log_event

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def require_database_url() -> str:
    """Return the configured database URL or fail fast with a clear message."""

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise EnvironmentError("DATABASE_URL 환경 변수가 필요합니다.")
    return database_url


def is_rag_sync_available() -> bool:
    """Check whether immediate RAG syncing can run in the current environment."""

    return bool(os.environ.get("DATABASE_URL"))


def get_connection() -> psycopg.Connection:
    """Open a fresh Postgres connection for one indexing or search operation."""

    return psycopg.connect(require_database_url())


def ensure_schema(*, recreate: bool = False) -> None:
    """Create the pgvector schema used by RAG.

    `recreate=True` is meant for full rebuilds, usually via the explicit index build
    endpoint. In normal sync mode we keep the table and only ensure it exists.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            if recreate:
                cur.execute("DROP TABLE IF EXISTS rag_documents")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_documents (
                    doc_id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    category TEXT,
                    title TEXT,
                    content TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    embedding VECTOR(1536) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS rag_documents_source_type_idx ON rag_documents (source_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS rag_documents_post_id_idx ON rag_documents (post_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS rag_documents_category_idx ON rag_documents (category)")
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS rag_documents_embedding_idx
                ON rag_documents USING hnsw (embedding vector_cosine_ops)
                """
            )
        conn.commit()


def chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split long source text into overlapping chunks for embedding.

    The overlap helps preserve context across chunk boundaries so semantic search does
    not lose important phrases that happen to fall near the split point.
    """

    normalized = text.strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunks.append(normalized[start:end].strip())
        if end >= len(normalized):
            break
        start = max(0, end - chunk_overlap)
    return [chunk for chunk in chunks if chunk]


def flatten_text(value: Any) -> list[str]:
    """Flatten nested JSON-style data into a list of searchable text lines.

    `post_style` files are structured objects, but vector search needs one plain-text
    representation. This helper recursively walks the structure and preserves keys so
    the resulting text still carries some field-level meaning.
    """

    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            lines.extend(flatten_text(item))
        return lines
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            nested = flatten_text(item)
            if nested:
                lines.append(str(key))
                lines.extend(nested)
        return lines
    return [str(value)]


def build_source_documents_from_post(
    source_post: SourcePost,
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
) -> list[IndexedDocument]:
    """Turn one raw source post into multiple searchable chunk documents."""

    post_id = str(source_post.metadata.get("post_id", ""))
    title = source_post.metadata.get("title") if isinstance(source_post.metadata.get("title"), str) else None
    category = source_post.metadata.get("category") if isinstance(source_post.metadata.get("category"), str) else None
    chunks = chunk_text(source_post.post_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    documents: list[IndexedDocument] = []
    for index, chunk in enumerate(chunks):
        documents.append(
            IndexedDocument(
                doc_id=f"source:{post_id}:{index}",
                post_id=post_id,
                source_type="source_chunk",
                category=category,
                title=title,
                content=chunk,
                metadata={"chunk_index": index},
            )
        )
    return documents


def build_post_style_document_from_payload(payload: dict[str, Any], fallback_post_id: str | None = None) -> IndexedDocument:
    """Convert one structured `post_style` payload into a single searchable document."""

    post_id = str(payload.get("post_id") or fallback_post_id or "unknown")
    category = payload.get("category") if isinstance(payload.get("category"), str) else None
    title = payload.get("title") if isinstance(payload.get("title"), str) else None
    lines = flatten_text(payload)
    return IndexedDocument(
        doc_id=f"post_style:{post_id}",
        post_id=post_id,
        source_type="post_style",
        category=category,
        title=title,
        content="\n".join(lines),
        metadata={"keys": sorted(payload.keys())},
    )


def build_source_documents(sources_dir: Path, *, chunk_size: int, chunk_overlap: int) -> list[IndexedDocument]:
    """Load all saved source text files and expand them into chunk documents."""

    documents: list[IndexedDocument] = []
    for path in sorted(sources_dir.glob("*.txt")):
        post_id = path.stem
        text = load_text(path)
        source_post = SourcePost(metadata={"post_id": post_id}, post_text=text)
        documents.extend(build_source_documents_from_post(source_post, chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    return documents


def build_post_style_documents(post_styles_dir: Path) -> list[IndexedDocument]:
    """Load all saved post_style JSON files and convert them into search documents."""

    documents: list[IndexedDocument] = []
    for path in sorted(post_styles_dir.glob("*.json")):
        payload = load_json(path)
        documents.append(build_post_style_document_from_payload(payload, fallback_post_id=path.stem))
    return documents


def build_documents(request: BuildIndexRequest, project_root: Path) -> list[IndexedDocument]:
    """Build the full document set used by a bulk index rebuild."""

    sources_dir = project_root / request.sources_dir
    post_styles_dir = project_root / request.post_styles_dir
    documents = build_source_documents(sources_dir, chunk_size=request.chunk_size, chunk_overlap=request.chunk_overlap)
    documents.extend(build_post_style_documents(post_styles_dir))
    return documents


def embed_texts(texts: list[str], *, model: str) -> list[list[float]]:
    """Embed texts in batches to keep API calls predictable and efficient."""

    client = build_openai_client()
    vectors: list[list[float]] = []
    batch_size = 32
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        response = create_embeddings(
            client=client,
            model=model,
            input=batch,
            metadata={"batch_size": len(batch)},
        )
        vectors.extend([item.embedding for item in response.data])
    return vectors


def upsert_documents(documents: list[IndexedDocument], embeddings: list[list[float]]) -> None:
    """Insert or update indexed documents in `rag_documents`.

    We use an upsert so repeated indexing of the same `doc_id` refreshes content and
    embeddings instead of creating duplicates.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            for document, embedding in zip(documents, embeddings, strict=True):
                cur.execute(
                    """
                    INSERT INTO rag_documents (
                        doc_id, post_id, source_type, category, title, content, metadata, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::vector)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        post_id = EXCLUDED.post_id,
                        source_type = EXCLUDED.source_type,
                        category = EXCLUDED.category,
                        title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """,
                    (
                        document.doc_id,
                        document.post_id,
                        document.source_type,
                        document.category,
                        document.title,
                        document.content,
                        json.dumps(document.metadata, ensure_ascii=False),
                        json.dumps(embedding),
                    ),
                )
        conn.commit()


def sync_documents(documents: list[IndexedDocument], *, embedding_model: str = DEFAULT_EMBEDDING_MODEL) -> dict[str, Any]:
    """Embed and upsert a small set of documents immediately.

    This is the fast path used right after source fetching or post_style extraction, so
    we do not need a second file-read pass just to refresh the vector index.
    """

    if not documents or not is_rag_sync_available():
        return {"synced_count": 0, "embedding_model": embedding_model}
    ensure_schema(recreate=False)
    embeddings = embed_texts([document.content for document in documents], model=embedding_model)
    upsert_documents(documents, embeddings)
    return {"synced_count": len(documents), "embedding_model": embedding_model}


def sync_source_post(source_post: SourcePost, *, embedding_model: str = DEFAULT_EMBEDDING_MODEL) -> dict[str, Any]:
    """Immediately sync one freshly fetched source post into the vector index."""

    documents = build_source_documents_from_post(source_post)
    result = sync_documents(documents, embedding_model=embedding_model)
    log_event(service="rag", event="sync.source_post", payload={
        "post_id": source_post.metadata.get("post_id"),
        **result,
    })
    return result


def sync_post_style_payload(post_style_payload: dict[str, Any], *, embedding_model: str = DEFAULT_EMBEDDING_MODEL) -> dict[str, Any]:
    """Immediately sync one freshly extracted post_style payload into the vector index."""

    document = build_post_style_document_from_payload(post_style_payload)
    result = sync_documents([document], embedding_model=embedding_model)
    log_event(service="rag", event="sync.post_style", payload={
        "post_id": post_style_payload.get("post_id"),
        **result,
    })
    return result


def build_index(*, project_root: Path, request: BuildIndexRequest) -> dict[str, Any]:
    """Rebuild the entire RAG index from files already stored in the project."""

    ensure_schema(recreate=request.recreate)
    documents = build_documents(request, project_root)
    if not documents:
        return {
            "indexed_count": 0,
            "source_chunk_count": 0,
            "post_style_count": 0,
            "embedding_model": request.embedding_model,
        }

    embeddings = embed_texts([document.content for document in documents], model=request.embedding_model)
    upsert_documents(documents, embeddings)
    return {
        "indexed_count": len(documents),
        "source_chunk_count": len([document for document in documents if document.source_type == "source_chunk"]),
        "post_style_count": len([document for document in documents if document.source_type == "post_style"]),
        "embedding_model": request.embedding_model,
    }


def search_documents(*, request: SearchRequest) -> list[SearchHit]:
    """Run vector similarity search with optional metadata filters."""

    query_embedding = embed_texts([request.query], model=request.embedding_model)[0]
    conditions: list[str] = []
    filter_params: list[Any] = []

    if request.source_types:
        conditions.append("source_type = ANY(%s)")
        filter_params.append(request.source_types)
    if request.category:
        conditions.append("category = %s")
        filter_params.append(request.category)
    if request.post_id:
        conditions.append("post_id = %s")
        filter_params.append(request.post_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT doc_id, post_id, source_type, category, title, content, metadata, embedding <=> %s::vector AS distance
        FROM rag_documents
        {where_clause}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    params = [json.dumps(query_embedding), *filter_params, json.dumps(query_embedding), request.limit]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    return [
        SearchHit(
            doc_id=row[0],
            post_id=row[1],
            source_type=row[2],
            category=row[3],
            title=row[4],
            content=row[5],
            metadata=row[6],
            distance=float(row[7]),
        )
        for row in rows
    ]
