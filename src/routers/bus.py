from fastapi import APIRouter

from src.models.bus import LlegadasBus, ParadaBus
from src.services.bus import get_llegadas_parada, get_parada

router = APIRouter()


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
    response_description="Información de parada de bus",
)
async def llegadas(num_parada: int) -> LlegadasBus:
    return get_llegadas_parada(num_parada)
