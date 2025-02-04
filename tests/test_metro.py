from fastapi.testclient import TestClient

from app import app
from models.metro import LlegadasMetro, ParadaMetro

client = TestClient(app)


def test_paradas():
    response = client.get("/metro/paradas")
    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert isinstance(data, list)
    assert all(ParadaMetro.model_validate(item) for item in data)


def test_llegadas():
    response = client.get("/metro/llegadas")
    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert isinstance(data, list)
    assert all(LlegadasMetro.model_validate(item) for item in data)


def test_llegadas_parada_not_found():
    response = client.get("/metro/llegadas/NotALine")
    assert response.status_code == 404  # noqa: PLR2004


def test_llegadas_parada_found():
    response = client.get("/metro/llegadas/105")
    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert LlegadasMetro.model_validate(data)
    assert isinstance(data["proximos"], list)
