from __future__ import annotations

"""Runtime helpers shared across services.

This module centralizes project-root based path handling so the rest of the code can
accept lightweight relative paths in API payloads and convert them into absolute
filesystem paths only when work actually starts.
"""

from pathlib import Path


# `core/` lives one level below the repository root, so we walk up once here.
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_project_path(path: str | Path) -> Path:
    """Return an absolute path anchored to the repository root when needed.

    Most API payloads store paths like `data/sources` instead of full absolute paths.
    Using this helper keeps request models simple while still allowing the service
    layer to work with concrete filesystem paths.
    """

    path = Path(path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def relative_to_project(path: Path) -> str:
    """Convert a path back into a project-relative string for response payloads.

    This is mainly used when we want logs or API responses to show stable, readable
    paths such as `data/outputs/foo.md` instead of machine-specific absolute paths.
    """

    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)
