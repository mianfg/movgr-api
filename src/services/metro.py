import json
import logging
import re

import urllib3
import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

from src.cache import get_cached, kv_get, kv_set, set_cached
from src.exceptions.exceptions import ParadaNotFoundError
from src.gtfs import metro_feed

logger = logging.getLogger(__name__)
urllib3.disable_warnings(InsecureRequestWarning)

_CACHE_KEY = "metro:llegadas"
_LAST_KEY = "metro:llegadas:last"
_DOWN_KEY = "metro:llegadas:down"
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


def _parse_cached(raw: str | None) -> list[LlegadasMetro] | None:
    if not raw:
        return None
    try:
        return [LlegadasMetro.model_validate(item) for item in json.loads(raw)]
    except Exception:
        return None


def _empty_llegadas() -> list[LlegadasMetro]:
    return [LlegadasMetro(parada=parada, proximos=[]) for parada in paradas]


def _fallback_llegadas() -> list[LlegadasMetro]:
    return _parse_cached(kv_get(_LAST_KEY)) or _empty_llegadas()


def get_llegadas() -> list[LlegadasMetro]:
    cached = _parse_cached(get_cached(_CACHE_KEY))
    if cached is not None:
        return cached
    if get_cached(_DOWN_KEY):
        return _fallback_llegadas()

    headers = {
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded",
        "dnt": "1",
        "origin": "https://metropolitanogranada.es",
        "priority": "u=0, i",
        "referer": "https://metropolitanogranada.es/horariosreal",
    }

    try:
        response = requests.post(
            "https://metropolitanogranada.es/MGhorariosreal.asp",
            headers=headers,
            timeout=12,
            verify=False,
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.warning("metro scrape timed out or failed; serving last good arrivals")
        set_cached(_DOWN_KEY, "1", ttl=30)
        return _fallback_llegadas()

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
    blob = json.dumps([item.model_dump(mode="json") for item in result])
    set_cached(_CACHE_KEY, blob)
    kv_set(_LAST_KEY, blob, 30 * 60)
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
