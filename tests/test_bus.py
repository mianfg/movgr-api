from fastapi.testclient import TestClient

from app import app
from models.bus import ParadaBusModel

client = TestClient(app)


def test_bus_line_not_found():
    response = client.get("/bus/230")
    assert response.status_code == 404  # noqa: PLR2004


def test_bus_line_found():
    response = client.get("/bus/249")
    assert response.status_code == 200  # noqa: PLR2004
    assert ParadaBusModel.model_validate(response.json())
