from __future__ import annotations

"""프로젝트 루트 기준 경로를 다루는 공통 유틸 모음."""

from pathlib import Path


# `core/` 바로 위를 프로젝트 루트로 사용한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_project_path(path: str | Path) -> Path:
    """상대 경로면 프로젝트 루트 기준 절대 경로로 바꾼다.

    API 요청에서는 `data/sources` 같은 상대 경로를 많이 쓰기 때문에,
    실제 서비스 로직에서는 이 함수를 통해 한 번만 절대 경로로 정리한다.
    """

    path = Path(path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path
