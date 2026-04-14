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
    """OPENAI_API_KEY가 없으면 바로 실패시킨다."""

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY 환경 변수가 필요합니다.")
    return api_key


def build_openai_client() -> OpenAI:
    """현재 환경 변수 기준으로 OpenAI 클라이언트를 만든다."""

    return OpenAI(api_key=require_api_key())


def schema_name_from_path(schema_path: Path, fallback: str) -> str:
    """스키마 파일명에서 OpenAI 응답 포맷 이름을 뽑아낸다."""

    stem = schema_path.stem
    if stem.endswith(".schema"):
        return stem[:-7]
    return fallback


def load_text(path: Path) -> str:
    """텍스트 파일을 UTF-8로 읽는다."""

    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    """JSON 파일을 읽어 딕셔너리로 돌려준다."""

    return json.loads(load_text(path))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    """딕셔너리를 JSON 파일로 저장한다."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def log_event(*, service: str, event: str, payload: dict[str, Any]) -> None:
    """서비스 이벤트를 JSONL 로그로 남긴다."""

    app_logger.write({
        "service": service,
        "event": event,
        "payload": payload,
    })


def record_openai_usage(*, operation: str, model: str, usage: Any, metadata: dict[str, Any] | None = None) -> None:
    """OpenAI 호출 사용량을 별도 JSONL 파일에 기록한다."""

    usage_store.record({
        "operation": operation,
        "model": model,
        "usage": extract_usage_dict(usage),
        "metadata": metadata or {},
    })


def create_response(*, client: OpenAI, model: str, input: list[dict[str, Any]], text: dict[str, Any] | None = None, metadata: dict[str, Any] | None = None):
    """Responses API 호출과 사용량 기록을 한 번에 처리한다."""

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
    """Embeddings API 호출과 사용량 기록을 한 번에 처리한다."""

    response = client.embeddings.create(model=model, input=input)
    record_openai_usage(
        operation="embeddings.create",
        model=model,
        usage=getattr(response, "usage", None),
        metadata=metadata,
    )
    return response
