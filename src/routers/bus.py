from fastapi import APIRouter

from src.models.bus import LineaBus, LlegadasBus, ParadaBus
from src.models.map import LineaBusDetail
from src.services.bus import (
    get_all_lineas,
    get_all_paradas,
    get_linea_detail,
    get_llegadas_parada,
    get_parada,
)

router = APIRouter()


@router.get(
    "/paradas",
    response_model=list[ParadaBus],
    response_description="Lista de paradas de bus con coordenadas",
)
async def paradas_list() -> list[ParadaBus]:
    return get_all_paradas()


@router.get(
    "/parada/{num_parada}",
    response_model=ParadaBus,
    response_description="Información de parada de bus",
)
async def parada(num_parada: int) -> ParadaBus:
    return get_parada(num_parada)


@router.get(
    "/llegadas/{num_parada}",
    response_model=LlegadasBus,
    response_description="Información de llegadas a parada de bus",
)
async def llegadas(num_parada: int) -> LlegadasBus:
    return get_llegadas_parada(num_parada)


@router.get(
    "/lineas",
    response_model=list[LineaBus],
    response_description="Lista de líneas de bus",
)
async def lineas_list() -> list[LineaBus]:
    return get_all_lineas()


@router.get(
    "/lineas/{id_linea}",
    response_model=LineaBusDetail,
    response_description="Detalle de línea de bus con forma de ruta",
)
async def linea_detail(id_linea: str) -> LineaBusDetail:
    return get_linea_detail(id_linea)
