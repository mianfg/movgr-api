from src.models.base import MovGrBaseModel
from src.models.map import RouteShape


class LineaCtagr(MovGrBaseModel):
    id: str
    nombre: str | None = None
    color: str | None = "FFFFFF"
    text_color: str | None = "15803d"


class VehiculoCtagr(MovGrBaseModel):
    linea: str
    sentido: int
    lat: float | None = None
    lon: float | None = None
    visto: str | None = None


class ProximoCtagr(MovGrBaseModel):
    linea: LineaCtagr
    destino: str
    hora: str
    minutos: int
    sentido: int | None = None
    en_ruta: bool = False


class ParadaCtagr(MovGrBaseModel):
    id: str
    nombre: str
    municipio: str | None = None
    nucleo: str | None = None
    lat: float | None = None
    lon: float | None = None
    lineas: list[str] | None = None


class LlegadasCtagr(MovGrBaseModel):
    parada: ParadaCtagr
    proximos: list[ProximoCtagr]
    vehiculos: list[VehiculoCtagr] = []


class LineaCtagrDetail(MovGrBaseModel):
    id: str
    nombre: str | None = None
    color: str | None = "FFFFFF"
    text_color: str | None = "15803d"
    shapes: list[RouteShape]
    vehiculos: list[VehiculoCtagr] = []
