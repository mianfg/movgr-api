from src.models.base import MovGrBaseModel


class ShapePoint(MovGrBaseModel):
    lat: float
    lon: float


class RouteShape(MovGrBaseModel):
    direction: int
    points: list[ShapePoint]


class LineaBusDetail(MovGrBaseModel):
    id: str
    nombre: str | None = None
    color: str | None = None
    text_color: str | None = None
    shapes: list[RouteShape]


class LineaMetroDetail(MovGrBaseModel):
    id: str
    nombre: str | None = None
    shapes: list[RouteShape]
