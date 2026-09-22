from __future__ import annotations

import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from src.cache import get_cached, set_cached
from src.exceptions.exceptions import LineaNotFoundError, ParadaNotFoundError
from src.models.ctagr import LineaCtagr, LineaCtagrDetail, LlegadasCtagr, ParadaCtagr, ProximoCtagr, VehiculoCtagr
from src.models.map import RouteShape, ShapePoint

logger = logging.getLogger(__name__)

_CTAN = "https://api.ctan.es/v1/Consorcios/3"
_BUSINFO = "https://ctagr.es/api/businfo/busInfoEnvia.php"
_REFERER = "https://ctagr.es/red-de-transporte/recorridos/businfo"
_TZ = ZoneInfo("Europe/Madrid")
_COLOR = "FFFFFF"
_TEXT = "15803d"
_NETWORK_TTL = 6 * 60 * 60
_LLEGADAS_TTL = 25
_LIVE_TTL = 25
_BUSINFO_TIMEOUT = 2.5

_session = requests.Session()
_session.headers.update({"User-Agent": "movGR/1.4"})


def _ctan(path: str, timeout: int = 12) -> dict:
    response = _session.get(f"{_CTAN}{path}", timeout=timeout)
    response.raise_for_status()
    return response.json()


def _businfo(params: dict) -> dict | None:
    cached_key = "ctagr:businfo:" + json.dumps(params, sort_keys=True, separators=(",", ":"))
    cached = get_cached(cached_key)
    if cached:
        return json.loads(cached)
    try:
        response = _session.get(
            _BUSINFO,
            params=params,
            headers={"Referer": _REFERER},
            timeout=_BUSINFO_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        logger.debug("ctagr live request failed: %s", params)
        return None
    if payload.get("E") not in {0, "0", None} and "lineas" not in payload and "posicion" not in payload:
        return None
    set_cached(cached_key, json.dumps(payload), _LIVE_TTL)
    return payload


def _minutes_until(hhmm: str, now: datetime | None = None) -> int:
    now = now or datetime.now(_TZ)
    hour, minute = (int(part) for part in hhmm.split(":")[:2])
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target < now - timedelta(minutes=1):
        target += timedelta(days=1)
    delta = int((target - now).total_seconds() // 60)
    return max(0, delta)


def _decode_dms(latitud: str | None, longitud: str | None) -> tuple[float | None, float | None]:
    if not latitud or not longitud:
        return None, None
    try:
        lat = float(latitud[1:3]) + float(latitud[3:5]) / 60 + float(latitud[5:]) / 3600
        lon = -(float(longitud[1:4]) + float(longitud[4:6]) / 60 + float(longitud[6:]) / 3600)
        return lat, lon
    except (ValueError, IndexError):
        return None, None


def _parse_polyline(raw: str | None) -> list[ShapePoint]:
    if not raw:
        return []
    points: list[ShapePoint] = []
    for chunk in raw.split("|"):
        if "," not in chunk:
            continue
        lon_s, lat_s = chunk.split(",", 1)
        try:
            points.append(ShapePoint(lat=float(lat_s), lon=float(lon_s)))
        except ValueError:
            continue
    return points


def _linea(codigo: str, nombre: str | None = None) -> LineaCtagr:
    return LineaCtagr(id=codigo, nombre=nombre, color=_COLOR, text_color=_TEXT)


def _network() -> dict:
    cached = get_cached("ctagr:network")
    if cached:
        return json.loads(cached)

    lineas_raw = _ctan("/lineas").get("lineas") or []
    paradas_raw = _ctan("/paradas").get("paradas") or []
    paradas = {
        str(item["idParada"]): {
            "id": str(item["idParada"]),
            "nombre": item.get("nombre") or "",
            "municipio": item.get("municipio"),
            "nucleo": item.get("nucleo"),
            "lat": float(item["latitud"]) if item.get("latitud") else None,
            "lon": float(item["longitud"]) if item.get("longitud") else None,
        }
        for item in paradas_raw
        if item.get("idParada") is not None
    }
    lines = [
        {
            "idLinea": str(item["idLinea"]),
            "codigo": item.get("codigo") or str(item["idLinea"]),
            "nombre": (item.get("nombre") or "").strip() or None,
        }
        for item in lineas_raw
    ]
    lines_at_stop: dict[str, list[str]] = defaultdict(list)
    stops_of_line: dict[str, list[dict]] = {}
    codigo_by_internal = {item["idLinea"]: item["codigo"] for item in lines}

    def fetch_line_stops(line: dict) -> tuple[str, list[dict]]:
        payload = _ctan(f"/lineas/{line['idLinea']}/paradas")
        return line["codigo"], payload.get("paradas") or []

    with ThreadPoolExecutor(max_workers=8, thread_name_prefix="ctagr") as pool:
        futures = [pool.submit(fetch_line_stops, line) for line in lines]
        for future in as_completed(futures):
            codigo, stops = future.result()
            stops_of_line[codigo] = stops
            for stop in stops:
                pid = str(stop.get("idParada"))
                if pid not in paradas and stop.get("latitud"):
                    paradas[pid] = {
                        "id": pid,
                        "nombre": stop.get("nombre") or "",
                        "municipio": None,
                        "nucleo": None,
                        "lat": float(stop["latitud"]),
                        "lon": float(stop["longitud"]) if stop.get("longitud") else None,
                    }
                if codigo not in lines_at_stop[pid]:
                    lines_at_stop[pid].append(codigo)

    assembled = {
        "paradas": paradas,
        "lines": lines,
        "lines_at_stop": dict(lines_at_stop),
        "stops_of_line": stops_of_line,
        "codigo_by_internal": codigo_by_internal,
        "internal_by_codigo": {item["codigo"]: item["idLinea"] for item in lines},
        "nombre_by_codigo": {item["codigo"]: item["nombre"] for item in lines},
    }
    set_cached("ctagr:network", json.dumps(assembled), _NETWORK_TTL)
    return assembled


def get_all_paradas() -> list[ParadaCtagr]:
    network = _network()
    result = []
    for stop in network["paradas"].values():
        result.append(
            ParadaCtagr(
                id=stop["id"],
                nombre=stop["nombre"],
                municipio=stop.get("municipio"),
                nucleo=stop.get("nucleo"),
                lat=stop.get("lat"),
                lon=stop.get("lon"),
                lineas=network["lines_at_stop"].get(stop["id"]) or [],
            )
        )
    return sorted(result, key=lambda item: (item.nombre, item.id))


def get_all_lineas() -> list[LineaCtagr]:
    network = _network()
    return [_linea(item["codigo"], item["nombre"]) for item in network["lines"]]


def get_parada(stop_id: str) -> ParadaCtagr:
    network = _network()
    stop = network["paradas"].get(str(stop_id))
    if not stop:
        raise ParadaNotFoundError
    return ParadaCtagr(
        id=stop["id"],
        nombre=stop["nombre"],
        municipio=stop.get("municipio"),
        nucleo=stop.get("nucleo"),
        lat=stop.get("lat"),
        lon=stop.get("lon"),
        lineas=network["lines_at_stop"].get(stop["id"]) or [],
    )


def _vehicles_for_line(internal_id: str) -> list[VehiculoCtagr]:
    network = _network()
    codigo = network["codigo_by_internal"].get(str(internal_id), str(internal_id))
    found: list[VehiculoCtagr] = []
    seen: set[tuple] = set()
    for sentido in (1, 2):
        payload = _businfo({"accion": "infoLinea", "idlinea": internal_id, "sentido": sentido})
        if not payload:
            continue
        for item in payload.get("posicion") or []:
            key = (item.get("idtpc"), item.get("horaoperacion"), sentido)
            if key in seen:
                continue
            seen.add(key)
            lat, lon = _decode_dms(item.get("latitud"), item.get("longitud"))
            found.append(
                VehiculoCtagr(
                    linea=codigo,
                    sentido=int(item.get("sentido") or sentido),
                    lat=lat,
                    lon=lon,
                    visto=item.get("hora") or item.get("horaoperacion"),
                )
            )
    return found


def get_llegadas_parada(stop_id: str) -> LlegadasCtagr:
    cache_key = f"ctagr:llegadas:{stop_id}"
    cached = get_cached(cache_key)
    if cached:
        return LlegadasCtagr.model_validate_json(cached)

    parada = get_parada(stop_id)
    network = _network()
    try:
        payload = _ctan(f"/paradas/{stop_id}/servicios")
    except Exception:
        logger.warning("ctagr servicios failed for %s", stop_id)
        payload = {"servicios": []}

    live_by_line: dict[str, list[VehiculoCtagr]] = {}
    internals = {
        network["internal_by_codigo"][codigo]
        for codigo in (parada.lineas or [])
        if codigo in network["internal_by_codigo"]
    }
    if internals:
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="ctagr-live") as pool:
            futures = [pool.submit(_vehicles_for_line, internal) for internal in internals]
            for future in as_completed(futures):
                try:
                    vehicles = future.result()
                except Exception:
                    continue
                if vehicles:
                    live_by_line[vehicles[0].linea] = vehicles

    now = datetime.now(_TZ)
    proximos: list[ProximoCtagr] = []
    for item in payload.get("servicios") or []:
        codigo = item.get("linea") or network["codigo_by_internal"].get(str(item.get("idLinea")), "")
        if not codigo:
            continue
        hora = item.get("servicio") or ""
        if not hora:
            continue
        sentido = int(item["sentido"]) if str(item.get("sentido") or "").isdigit() else None
        vehicles = live_by_line.get(codigo) or []
        en_ruta = any(vehicle.sentido == sentido for vehicle in vehicles) if sentido else bool(vehicles)
        proximos.append(
            ProximoCtagr(
                linea=_linea(codigo, network["nombre_by_codigo"].get(codigo) or item.get("nombre")),
                destino=item.get("destino") or item.get("nombre") or codigo,
                hora=hora,
                minutos=_minutes_until(hora, now),
                sentido=sentido,
                en_ruta=en_ruta,
            )
        )
    proximos.sort(key=lambda item: (item.minutos, item.hora, item.linea.id))
    vehiculos = [vehicle for group in live_by_line.values() for vehicle in group]
    result = LlegadasCtagr(parada=parada, proximos=proximos, vehiculos=vehiculos)
    set_cached(cache_key, result.model_dump_json(), _LLEGADAS_TTL)
    return result


def get_linea_detail(codigo: str) -> LineaCtagrDetail:
    network = _network()
    if codigo not in network["internal_by_codigo"]:
        raise LineaNotFoundError
    shapes: list[RouteShape] = []
    for sentido in (1, 2):
        ordered = [
            stop
            for stop in network["stops_of_line"].get(codigo, [])
            if str(stop.get("sentido")) == str(sentido) and stop.get("latitud")
        ]
        ordered.sort(key=lambda item: item.get("orden") or 0)
        points = [
            ShapePoint(lat=float(stop["latitud"]), lon=float(stop["longitud"]))
            for stop in ordered
            if stop.get("longitud")
        ]
        if points:
            shapes.append(RouteShape(direction=sentido, points=points))
    return LineaCtagrDetail(
        id=codigo,
        nombre=network["nombre_by_codigo"].get(codigo),
        color=_COLOR,
        text_color=_TEXT,
        shapes=shapes,
        vehiculos=[],
    )
