from src.models.base import MovGrBaseModel


class LineaBus(MovGrBaseModel):
    id: str
    nombre: str | None = None
    color: str | None = None
    text_color: str | None = None


class ProximoBus(MovGrBaseModel):
    linea: LineaBus
    destino: str
    minutos: int


class ParadaBus(MovGrBaseModel):
    id: int
    nombre: str
    lat: float | None = None
    lon: float | None = None
    lineas: list[str] | None = None


class LlegadasBus(MovGrBaseModel):
    parada: ParadaBus
    proximos: list[ProximoBus]
