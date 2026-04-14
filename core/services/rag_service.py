from __future__ import annotations

from typing import Any

from core.runtime import PROJECT_ROOT
from core.schemas.rag import BuildIndexRequest, SearchRequest
from core.services.common import log_event
from core.services.rag import build_index, search_documents


def health_payload() -> dict[str, str]:
    return {"service": "rag", "status": "ok"}


def build_index_job(payload: BuildIndexRequest) -> dict[str, Any]:
    result = build_index(project_root=PROJECT_ROOT, request=payload)
    log_event(service="rag", event="index.build", payload=result)
    return result


def retrieval_search_job(payload: SearchRequest) -> dict[str, Any]:
    hits = search_documents(request=payload)
    result = {
        "count": len(hits),
        "hits": [hit.model_dump() for hit in hits],
    }
    log_event(service="rag", event="retrieval.search", payload={"query": payload.query, "count": result["count"]})
    return result
