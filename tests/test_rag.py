import json
from pathlib import Path

from core.schemas.rag import BuildIndexRequest
from core.services.generation import build_generation_query
from core.services.rag import build_documents, chunk_text
from core.schemas.orchestrator import GenerateRequest


def test_chunk_text_splits_text() -> None:
    text = "abcdefghij" * 5
    chunks = chunk_text(text, chunk_size=12, chunk_overlap=2)
    assert len(chunks) >= 4
    assert all(chunks)


def test_build_documents_includes_source_chunks_and_post_styles(tmp_path: Path) -> None:
    sources_dir = tmp_path / "sources"
    post_styles_dir = tmp_path / "post_styles"
    sources_dir.mkdir()
    post_styles_dir.mkdir()

    (sources_dir / "123.txt").write_text("sample source text" * 50, encoding="utf-8")
    (post_styles_dir / "123.json").write_text(
        json.dumps({"post_id": "123", "title": "title", "category": "육아 정보", "tone": {"primary": ["편안함"]}}, ensure_ascii=False),
        encoding="utf-8",
    )

    request = BuildIndexRequest(
        sources_dir=str(sources_dir.relative_to(tmp_path)),
        post_styles_dir=str(post_styles_dir.relative_to(tmp_path)),
        chunk_size=30,
        chunk_overlap=5,
    )
    documents = build_documents(request, tmp_path)
    source_types = {document.source_type for document in documents}
    assert "source_chunk" in source_types
    assert "post_style" in source_types


def test_build_generation_query_contains_request_fields() -> None:
    request = GenerateRequest(
        topic="실리콘 턱받이",
        category="육아 정보",
        intent="후기 작성",
        audience="초보 부모",
        key_points=["세척", "휴대성"],
    )
    query = build_generation_query(request)
    assert "실리콘 턱받이" in query
    assert "육아 정보" in query
    assert "세척" in query
