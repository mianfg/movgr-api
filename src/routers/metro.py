from fastapi import APIRouter

from src.models.metro import LlegadasMetro, ParadaMetro
from src.services.metro import get_llegadas, get_llegadas_parada
from src.services.metro import paradas as paradas_metro

router = APIRouter()


@router.get(
    "/paradas",
    response_model=list[ParadaMetro],
    response_description="Lista de paradas de metro",
)
async def paradas() -> list[ParadaMetro]:
    return paradas_metro


@router.get(
    "/llegadas",
    response_model=list[LlegadasMetro],
    response_description="Obtener estado actual de todas las paradas de metro",
)
async def llegadas() -> list[LlegadasMetro]:
    return get_llegadas()


@router.get(
    "/llegadas/{id_parada}",
    response_model=LlegadasMetro,
    response_description="Información de parada de metro",
)
async def llegadas_parada(id_parada: str) -> LlegadasMetro:
    return get_llegadas_parada(id_parada)
