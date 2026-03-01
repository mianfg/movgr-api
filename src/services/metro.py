import json
import re

import requests
from bs4 import BeautifulSoup

from src.cache import get_cached, set_cached
from src.exceptions.exceptions import ParadaNotFoundError
from src.gtfs import metro_feed
from src.models.map import LineaMetroDetail, RouteShape, ShapePoint
from src.models.metro import (
    LlegadasMetro,
    ParadaMetro,
    ProximoMetro,
)


def _build_paradas() -> list[ParadaMetro]:
    stops = sorted(metro_feed.stops_by_id.values(), key=lambda s: int(s.stop_id))
    return [
        ParadaMetro(
            linea="1",
            id=stop.stop_id,
            nombre=stop.stop_name,
            lat=stop.stop_lat,
            lon=stop.stop_lon,
        )
        for stop in stops
    ]


paradas = _build_paradas()


def get_llegadas() -> list[LlegadasMetro]:
    cache_key = "metro:llegadas"
    cached = get_cached(cache_key)
    if cached:
        return [LlegadasMetro.model_validate(item) for item in json.loads(cached)]

    headers = {
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded",
        "dnt": "1",
        "origin": "https://metropolitanogranada.es",
        "priority": "u=0, i",
        "referer": "https://metropolitanogranada.es/horariosreal",
    }

    response = requests.post(
        "https://metropolitanogranada.es/MGhorariosreal.asp",
        headers=headers,
        timeout=5,
        verify=False,
    )
    response.encoding = response.apparent_encoding

    soup = BeautifulSoup(response.text, "html.parser")

    datos = [cell.getText().strip() for cell in soup.find_all("td")]
    paradas_soup = [datos[i : i + 5] for i in range(0, len(datos), 5)]

    for parada in paradas_soup:
        parada[1:] = ["".join(re.findall(r"\d+", col)) for col in parada[1:]]

    result = [
        LlegadasMetro(
            parada=parada,
            proximos=sorted(
                [
                    ProximoMetro(
                        direccion="Armilla" if i >= 2 else "Albolote",  # noqa: PLR2004
                        minutos=int(col),
                    )
                    for i, col in enumerate(parada_soup[1:])
                    if col
                ],
                key=lambda proximo: proximo.minutos,
            ),
        )
        for parada_soup, parada in zip(paradas_soup, paradas)
    ]
    set_cached(cache_key, json.dumps([item.model_dump(mode="json") for item in result]))
    return result


def get_llegadas_parada(id_parada: str) -> LlegadasMetro:
    proximos = get_llegadas()
    for proximo in proximos:
        if proximo.parada.id == id_parada:
            return proximo
    raise ParadaNotFoundError from None


def get_linea_detail() -> LineaMetroDetail:
    route = metro_feed.routes_by_short_name.get("1")
    nombre = route.route_long_name if route else None

    direction_shapes = metro_feed.route_shapes.get("1", {})
    shapes = [
        RouteShape(
            direction=d,
            points=[ShapePoint(lat=p.lat, lon=p.lon) for p in pts],
        )
        for d, pts in sorted(direction_shapes.items())
    ]
    return LineaMetroDetail(id="1", nombre=nombre, shapes=shapes)
