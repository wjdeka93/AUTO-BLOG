from __future__ import annotations

from pathlib import Path

from core.models import SourcePost
from core.services.naver_blog import fetch_naver_post
from core.services.rag import sync_source_post


def load_urls(urls_file: Path) -> list[str]:
    """URL 파일에서 빈 줄을 제외한 실제 URL만 읽어온다."""

    return [line.strip() for line in urls_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def fetch_and_save_source(url: str, output_dir: Path) -> SourcePost:
    """블로그 원문을 가져와 텍스트 파일로 저장하고 즉시 RAG에도 반영한다."""

    source_post = fetch_naver_post(url)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_path = output_dir / f"{source_post.metadata['post_id']}.txt"
    source_path.write_text(source_post.post_text, encoding="utf-8")
    sync_source_post(source_post)
    return source_post


def fetch_all_sources(urls_file: Path, output_dir: Path) -> list[SourcePost]:
    """URL 목록 전체를 순회하며 source 파일을 만든다."""

    posts: list[SourcePost] = []
    for url in load_urls(urls_file):
        posts.append(fetch_and_save_source(url, output_dir))
    return posts
