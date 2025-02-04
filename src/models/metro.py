from enum import Enum

from pydantic import Field

from src.models.base import MovGrBaseModel


class DireccionMetro(Enum):
    Albolote = "Albolote"
    Armilla = "Armilla"


class ProximoMetro(MovGrBaseModel):
    direccion: DireccionMetro
    minutos: int = Field(ge=0)


class ParadaMetro(MovGrBaseModel):
    linea: str
    id: str
    nombre: str


class LlegadasMetro(MovGrBaseModel):
    parada: ParadaMetro
    proximos: list[ProximoMetro]
