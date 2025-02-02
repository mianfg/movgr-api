from fastapi.testclient import TestClient

from app import app
from models.metro import ParadaMetroModel

client = TestClient(app)


def test_metro_line_not_found():
    response = client.get("/metro/NotALine")
    assert response.status_code == 404  # noqa: PLR2004


def test_bus_line_found():
    response = client.get("/metro/Recogidas")
    assert response.status_code == 200  # noqa: PLR2004
    assert ParadaMetroModel.model_validate(response.json())
