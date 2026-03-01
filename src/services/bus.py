import requests
from bs4 import BeautifulSoup

from src.cache import get_cached, set_cached
from src.exceptions.exceptions import (
    LineaNotFoundError,
    ParadaNotFoundError,
    ParadaRequestError,
)
from src.gtfs import bus_feed
from src.models.bus import LineaBus, LlegadasBus, ParadaBus, ProximoBus
from src.models.map import LineaBusDetail, RouteShape, ShapePoint


def _build_paradas() -> dict[int, ParadaBus]:
    result: dict[int, ParadaBus] = {}
    for code, stop in bus_feed.stops_by_code.items():
        try:
            stop_id = int(code)
        except ValueError:
            continue
        route_names = sorted(bus_feed.stop_route_names.get(code, set()))
        result[stop_id] = ParadaBus(
            id=stop_id,
            nombre=stop.stop_name,
            lat=stop.stop_lat,
            lon=stop.stop_lon,
            lineas=route_names or None,
        )
    return result


def _build_lineas() -> dict[str, LineaBus]:
    return {
        short: LineaBus(
            id=short,
            nombre=route.route_long_name or None,
            color=route.route_color or None,
            text_color=route.route_text_color or None,
        )
        for short, route in bus_feed.routes_by_short_name.items()
    }


paradas = _build_paradas()
lineas = _build_lineas()


def get_parada(id_parada: int) -> ParadaBus:
    """Return stop info from GTFS data, falling back to scraping."""
    if id_parada in paradas:
        return paradas[id_parada]

    cache_key = f"bus:parada:{id_parada}"
    cached = get_cached(cache_key)
    if cached:
        return ParadaBus.model_validate_json(cached)

    try:
        response = __perform_request(id_parada)
        soup = BeautifulSoup(response.text, "html.parser")
        result = __extract_parada_from_soup(soup, id_parada)
        set_cached(cache_key, result.model_dump_json())
        return result
    except ParadaRequestError:
        raise ParadaNotFoundError from None


def get_linea(id_linea: str) -> LineaBus:
    try:
        return lineas[id_linea]
    except KeyError:
        raise LineaNotFoundError from None


def get_all_paradas() -> list[ParadaBus]:
    return list(paradas.values())


def get_all_lineas() -> list[LineaBus]:
    return list(lineas.values())


def get_linea_detail(id_linea: str) -> LineaBusDetail:
    if id_linea not in lineas:
        raise LineaNotFoundError from None

    linea = lineas[id_linea]
    direction_shapes = bus_feed.route_shapes.get(id_linea, {})
    shapes = [
        RouteShape(
            direction=d,
            points=[ShapePoint(lat=p.lat, lon=p.lon) for p in pts],
        )
        for d, pts in sorted(direction_shapes.items())
    ]
    return LineaBusDetail(
        id=linea.id,
        nombre=linea.nombre,
        color=linea.color,
        text_color=linea.text_color,
        shapes=shapes,
    )


def __extract_parada_from_soup(soup: BeautifulSoup, id_parada: int) -> ParadaBus:
    """Extract parada information from BeautifulSoup object."""
    message = soup.find("div", {"class": "message"})
    if message and "no existe" in message.getText():
        raise ParadaNotFoundError from None

    mainhead = soup.find("div", {"class": "mainhead"})
    if mainhead:
        nombre_div = mainhead.find("div", {"style": lambda x: x and "color:" in x})
        if nombre_div:
            nombre_parada = nombre_div.getText().strip()
            nombre_parada = " ".join(nombre_parada.split())
            return ParadaBus(id=id_parada, nombre=nombre_parada)

    raise ParadaNotFoundError from None


def __perform_request(num_parada: int) -> dict:
    headers = {
        "accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
            "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        ),
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "max-age=0",
        "dnt": "1",
        "origin": "https://www.transportesrober.com",
        "referer": "https://www.transportesrober.com/flotamovimiento/paradas.htm",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "upgrade-insecure-requests": "1",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        ),
    }

    files = {
        "excel": (None, ""),
        "parada": (None, str(num_parada)),
    }

    response = requests.post(
        "https://www.transportesrober.com/flotamovimiento/paradas.htm",
        headers=headers,
        files=files,
        timeout=5,
    )

    if response.status_code != 200:  # noqa: PLR2004
        raise ParadaRequestError

    response.encoding = "utf-8"
    return response


def get_llegadas_parada(num_parada: int) -> LlegadasBus:
    cache_key = f"bus:llegadas:{num_parada}"
    cached = get_cached(cache_key)
    if cached:
        return LlegadasBus.model_validate_json(cached)

    req = __perform_request(num_parada)
    soup = BeautifulSoup(req.text, "html.parser")

    parada = __extract_parada_from_soup(soup, num_parada)

    message = soup.find("div", {"class": "message"})
    if message:
        return LlegadasBus(parada=parada, proximos=[])

    proximos: list[ProximoBus] = []
    table = soup.find("div", {"class": "tf"})
    if table:
        rows = table.find_all("div", {"class": "tfr"})
        for row in rows:
            cols = row.find_all("div", {"class": "tfcc"})
            cols_s = row.find_all("div", {"class": "tfccs"})
            if len(cols) >= 3 and len(cols_s) >= 1:  # noqa: PLR2004
                form_white_div = cols[0].find("div", {"class": "form_white"})
                if form_white_div:
                    id_linea = form_white_div.getText().strip()
                    try:
                        linea = get_linea(id_linea)
                    except LineaNotFoundError:
                        linea = LineaBus(id=id_linea)
                    destino = cols_s[0].getText().strip()
                    minutos_text = cols[1].getText().strip()
                    minutos = int(minutos_text) if minutos_text.isdigit() else 0
                    proximos.append(
                        ProximoBus(
                            linea=linea,
                            destino=destino,
                            minutos=minutos,
                        ),
                    )

    result = LlegadasBus(parada=parada, proximos=proximos)
    set_cached(cache_key, result.model_dump_json())
    return result
