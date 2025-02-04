from fastapi.testclient import TestClient

from app import app
from models.bus import LlegadasBus, ParadaBus

client = TestClient(app)


def test_parada_not_found():
    response = client.get("/bus/parada/230")
    assert response.status_code == 404  # noqa: PLR2004


def test_parada_found():
    response = client.get("/bus/parada/249")
    assert response.status_code == 200  # noqa: PLR2004
    assert ParadaBus.model_validate(response.json())


def test_llegadas_not_found():
    response = client.get("/bus/llegadas/230")
    assert response.status_code == 404  # noqa: PLR2004


def test_llegadas_found():
    response = client.get("/bus/llegadas/249")
    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert LlegadasBus.model_validate(data)
    assert isinstance(data["proximos"], list)
