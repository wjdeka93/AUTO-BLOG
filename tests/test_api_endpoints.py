from fastapi.testclient import TestClient

from apps.orchestrator.main import app as orchestrator_app
from apps.rag.main import app as rag_app


def test_orchestrator_healthz() -> None:
    client = TestClient(orchestrator_app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "orchestrator"


def test_rag_healthz() -> None:
    client = TestClient(rag_app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "rag"
