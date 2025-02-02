"""Router para metro."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from src.models.metro import ParadaMetroModel
from src.services.metro import get_parada_metro
from src.services.vcard import make_vcard_metro

router = APIRouter()


@router.get(
    "/{nombre_parada}",
    response_model=ParadaMetroModel,
    response_description="Información de parada de metro",
)
async def metro(nombre_parada: str) -> ParadaMetroModel:
    """Obtener información de parada de metro."""
    return get_parada_metro(nombre_parada, fuzzy=True)


@router.get(
    "/{nombre_parada}/vcard",
    response_class=PlainTextResponse,
    response_description="Información de parada de metro, en VCARD",
)
async def metro_vcard(nombre_parada: str) -> str:
    """Obtener información de parada de metro, en VCARD."""
    return make_vcard_metro(get_parada_metro(nombre_parada, fuzzy=True))
