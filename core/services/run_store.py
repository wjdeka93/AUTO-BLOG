from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from core.schemas.orchestrator import RunRecord


class RunStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def create(self, *, run_type: str, payload: dict) -> RunRecord:
        record = RunRecord(
            run_id=uuid4().hex,
            run_type=run_type,
            status="running",
            started_at=self._now(),
            input=payload,
        )
        self.save(record)
        return record

    def complete(self, record: RunRecord, *, output: dict) -> RunRecord:
        updated = record.model_copy(update={
            "status": "completed",
            "finished_at": self._now(),
            "output": output,
        })
        self.save(updated)
        return updated

    def fail(self, record: RunRecord, *, error: str) -> RunRecord:
        updated = record.model_copy(update={
            "status": "failed",
            "finished_at": self._now(),
            "error": error,
        })
        self.save(updated)
        return updated

    def get(self, run_id: str) -> RunRecord:
        path = self.root_dir / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(run_id)
        return RunRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, record: RunRecord) -> None:
        path = self.root_dir / f"{record.run_id}.json"
        path.write_text(json.dumps(record.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

