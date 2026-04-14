from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourcePost:
    metadata: dict[str, Any]
    post_text: str


@dataclass(frozen=True)
class PipelinePaths:
    project_root: Path
    urls_file: Path
    sources_dir: Path
    post_styles_dir: Path
    main_style_file: Path
    sub_style_file: Path


@dataclass(frozen=True)
class PostStyleTask:
    url: str
    output_file: Path
    source_output_file: Path
