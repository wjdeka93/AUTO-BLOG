from pathlib import Path

from core.schemas.orchestrator import GenerateRequest
import core.services.generation as generation


class DummyHit:
    def __init__(self, idx: int) -> None:
        self.idx = idx

    def model_dump(self) -> dict[str, object]:
        return {"doc_id": f"doc-{self.idx}", "content": "retrieved"}


class DummyClient:
    class responses:
        @staticmethod
        def create(**kwargs):
            class Response:
                output_text = "# title\ncontent"
                usage = None
            return Response()



def test_generate_blog_post_includes_retrieval(tmp_path: Path, monkeypatch) -> None:
    styles_dir = tmp_path / "data" / "styles"
    prompts_dir = tmp_path / "prompts"
    styles_dir.mkdir(parents=True)
    prompts_dir.mkdir(parents=True)
    (styles_dir / "main_style.json").write_text('{"author": "a"}', encoding="utf-8")
    (styles_dir / "sub_style.json").write_text('{"grouped_styles": [{"group_name": "육아 정보"}]}', encoding="utf-8")
    (prompts_dir / "blog_generation.txt").write_text("prompt", encoding="utf-8")

    monkeypatch.setattr(generation, "build_openai_client", lambda: DummyClient())
    monkeypatch.setattr(generation, "search_documents", lambda request: [DummyHit(1), DummyHit(2)])
    monkeypatch.setattr(generation, "create_response", lambda **kwargs: DummyClient.responses.create())

    result = generation.generate_blog_post(
        project_root=tmp_path,
        request=GenerateRequest(
            topic="턱받이",
            category="육아 정보",
            intent="후기",
            audience="부모",
            key_points=["세척"],
        ),
    )
    assert result["retrieval_count"] == 2
    assert Path(result["output_file"]).exists()
