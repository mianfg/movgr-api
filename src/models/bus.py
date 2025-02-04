from src.models.base import MovGrBaseModel


class LineaBus(MovGrBaseModel):
    id: str
    nombre: str | None


class ProximoBus(MovGrBaseModel):
    linea: LineaBus
    destino: str
    minutos: int


class ParadaBus(MovGrBaseModel):
    id: int
    nombre: str


class LlegadasBus(MovGrBaseModel):
    parada: ParadaBus
    proximos: list[ProximoBus]
