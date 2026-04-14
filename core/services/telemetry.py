from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


class JsonlLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        ensure_parent(self.path)

    def write(self, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


class UsageStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        ensure_parent(self.path)

    def record(self, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def extract_usage_dict(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return usage

    result: dict[str, Any] = {}
    for key in [
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "prompt_tokens",
        "completion_tokens",
    ]:
        value = getattr(usage, key, None)
        if value is not None:
            result[key] = value
    return result
