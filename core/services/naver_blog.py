from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from core.models import SourcePost

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


def normalize_naver_blog_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    if "blogId" in query and "logNo" in query:
        blog_id = query["blogId"][0]
        log_no = query["logNo"][0]
        return f"https://m.blog.naver.com/{blog_id}/{log_no}", log_no

    path_parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc == "m.blog.naver.com" and len(path_parts) >= 2:
        blog_id, log_no = path_parts[0], path_parts[1]
        return f"https://m.blog.naver.com/{blog_id}/{log_no}", log_no

    raise ValueError(f"지원하지 않는 네이버 블로그 URL 형식입니다: {url}")


def fetch_url_text(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response.text


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u200b", "")
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def extract_text_list(elements: list[Any]) -> list[str]:
    lines: list[str] = []
    for element in elements:
        text = element.get_text("\n", strip=True)
        text = unescape(text)
        text = text.replace("\u200b", "").strip()
        if text:
            lines.append(text)
    return lines


def parse_naver_blog_mobile_html(html: str, normalized_url: str, post_id: str) -> SourcePost:
    soup = BeautifulSoup(html, "html.parser")

    title_meta = soup.find("meta", attrs={"property": "og:title"})
    title = title_meta.get("content", "").strip() if title_meta else ""

    category_tag = soup.select_one("div.blog_category a")
    category = normalize_whitespace(category_tag.get_text()) if category_tag else ""

    date_tag = soup.select_one("p.blog_date")
    published_at = normalize_whitespace(date_tag.get_text()) if date_tag else None

    author_meta = soup.find("meta", attrs={"property": "naverblog:nickname"})
    author = author_meta.get("content", "").strip() if author_meta else ""

    paragraphs = extract_text_list(soup.select("p.se-text-paragraph"))
    if not paragraphs:
        paragraphs = extract_text_list(soup.select("div.se-module-text p"))
    if not paragraphs:
        description_meta = soup.find("meta", attrs={"property": "og:description"})
        if description_meta and description_meta.get("content"):
            paragraphs = [normalize_whitespace(description_meta["content"])]

    if not title:
        raise ValueError("제목을 추출하지 못했습니다.")
    if not paragraphs:
        raise ValueError("본문 문단을 추출하지 못했습니다.")

    return SourcePost(
        metadata={
            "post_id": post_id,
            "url": normalized_url,
            "title": title,
            "published_at": published_at,
            "author": author,
            "category": category,
        },
        post_text="\n\n".join(paragraphs),
    )


def fetch_naver_post(url: str) -> SourcePost:
    normalized_url, post_id = normalize_naver_blog_url(url)
    html = fetch_url_text(normalized_url)
    return parse_naver_blog_mobile_html(html, normalized_url, post_id)

