from fastapi import APIRouter

from src.models.ctagr import LineaCtagr, LineaCtagrDetail, LlegadasCtagr, ParadaCtagr
from src.services.ctagr import (
    get_all_lineas,
    get_all_paradas,
    get_linea_detail,
    get_llegadas_parada,
    get_parada,
)

router = APIRouter()


@router.get("/paradas", response_model=list[ParadaCtagr])
async def paradas_list() -> list[ParadaCtagr]:
    return get_all_paradas()


@router.get("/parada/{id_parada}", response_model=ParadaCtagr)
async def parada(id_parada: str) -> ParadaCtagr:
    return get_parada(id_parada)


@router.get("/llegadas/{id_parada}", response_model=LlegadasCtagr)
async def llegadas(id_parada: str) -> LlegadasCtagr:
    return get_llegadas_parada(id_parada)


@router.get("/lineas", response_model=list[LineaCtagr])
async def lineas_list() -> list[LineaCtagr]:
    return get_all_lineas()


@router.get("/lineas/{id_linea}", response_model=LineaCtagrDetail)
async def linea_detail(id_linea: str) -> LineaCtagrDetail:
    return get_linea_detail(id_linea)
