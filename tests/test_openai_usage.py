from pathlib import Path
from types import SimpleNamespace

import core.services.common as common


class DummyUsage:
    input_tokens = 10
    output_tokens = 20
    total_tokens = 30


class DummyResponse:
    def __init__(self) -> None:
        self.output_text = "{}"
        self.usage = DummyUsage()


class DummyEmbeddingsResponse:
    def __init__(self) -> None:
        self.data = [SimpleNamespace(embedding=[0.1, 0.2])]
        self.usage = DummyUsage()


class DummyClient:
    class responses:
        @staticmethod
        def create(**kwargs):
            return DummyResponse()

    class embeddings:
        @staticmethod
        def create(**kwargs):
            return DummyEmbeddingsResponse()


def test_create_response_records_usage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(common, "usage_store", common.UsageStore(tmp_path / "usage.jsonl"))
    response = common.create_response(
        client=DummyClient(),
        model="gpt-5",
        input=[{"role": "user", "content": "hello"}],
        metadata={"kind": "test"},
    )
    assert response.output_text == "{}"
    content = (tmp_path / "usage.jsonl").read_text(encoding="utf-8")
    assert "responses.create" in content
    assert "gpt-5" in content


def test_create_embeddings_records_usage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(common, "usage_store", common.UsageStore(tmp_path / "usage.jsonl"))
    response = common.create_embeddings(
        client=DummyClient(),
        model="text-embedding-3-small",
        input=["hello"],
        metadata={"kind": "test"},
    )
    assert len(response.data) == 1
    content = (tmp_path / "usage.jsonl").read_text(encoding="utf-8")
    assert "embeddings.create" in content
