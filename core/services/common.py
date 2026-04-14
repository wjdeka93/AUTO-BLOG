from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from core.services.telemetry import JsonlLogger, UsageStore, extract_usage_dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = PROJECT_ROOT / "data" / "logs"
USAGE_DIR = PROJECT_ROOT / "data" / "usage"
app_logger = JsonlLogger(LOGS_DIR / "app.log")
usage_store = UsageStore(USAGE_DIR / "openai_usage.jsonl")


def require_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY 환경 변수가 필요합니다.")
    return api_key


def build_openai_client() -> OpenAI:
    return OpenAI(api_key=require_api_key())


def schema_name_from_path(schema_path: Path, fallback: str) -> str:
    stem = schema_path.stem
    if stem.endswith(".schema"):
        return stem[:-7]
    return fallback


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(load_text(path))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def log_event(*, service: str, event: str, payload: dict[str, Any]) -> None:
    app_logger.write({
        "service": service,
        "event": event,
        "payload": payload,
    })


def record_openai_usage(*, operation: str, model: str, usage: Any, metadata: dict[str, Any] | None = None) -> None:
    usage_store.record({
        "operation": operation,
        "model": model,
        "usage": extract_usage_dict(usage),
        "metadata": metadata or {},
    })


def create_response(*, client: OpenAI, model: str, input: list[dict[str, Any]], text: dict[str, Any] | None = None, metadata: dict[str, Any] | None = None):
    kwargs: dict[str, Any] = {
        "model": model,
        "input": input,
    }
    if text is not None:
        kwargs["text"] = text
    response = client.responses.create(**kwargs)
    record_openai_usage(
        operation="responses.create",
        model=model,
        usage=getattr(response, "usage", None),
        metadata=metadata,
    )
    return response


def create_embeddings(*, client: OpenAI, model: str, input: list[str], metadata: dict[str, Any] | None = None):
    response = client.embeddings.create(model=model, input=input)
    record_openai_usage(
        operation="embeddings.create",
        model=model,
        usage=getattr(response, "usage", None),
        metadata=metadata,
    )
    return response
