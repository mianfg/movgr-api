import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.cache import kv_delete, kv_get, kv_set, set_add, set_count, set_members, set_remove, try_lock
from src.models.bus import LlegadasBus
from src.models.live import LiveSubscribeRequest
from src.models.metro import DireccionMetro, LlegadasMetro
from src.services.apns import is_configured, send_live_update
from src.services.bus import get_llegadas_parada
from src.services.metro import get_llegadas

logger = logging.getLogger(__name__)

_TOKENS_KEY = "live:tokens"
_STOPS_KEY = "live:stops"
_SUB_PREFIX = "live:sub:"
_TTL = 2 * 60 * 60
_INTERVAL = 15
_memory: dict[str, dict] = {}
_last_fingerprint: dict[str, str] = {}
_apns_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="apns")


def _stop_member(kind: str, stop_id: str) -> str:
    return f"{kind}|{stop_id}"


def _stop_tokens_key(kind: str, stop_id: str) -> str:
    return f"live:stop:{kind}:{stop_id}"


def _parse_stop_member(member: str) -> tuple[str, str] | None:
    kind, sep, stop_id = member.partition("|")
    if not sep or not kind or not stop_id:
        return None
    return kind, stop_id


def _drop_from_stop(token: str, kind: str, stop_id: str) -> None:
    key = _stop_tokens_key(kind, stop_id)
    set_remove(key, token)
    if set_count(key) == 0:
        set_remove(_STOPS_KEY, _stop_member(kind, stop_id))


def subscribe(request: LiveSubscribeRequest) -> None:
    token = request.token.strip().lower()
    payload = {
        "token": token,
        "environment": request.environment if request.environment in {"sandbox", "production"} else "production",
        "kind": request.kind,
        "stop_id": request.stop_id,
        "preferred_line_id": request.preferred_line_id or None,
        "metro_direction": request.metro_direction or "Armilla",
        "metro_inverted": bool(request.metro_inverted),
    }
    previous = _load_subscription(token)
    if previous and (previous.get("kind") != payload["kind"] or previous.get("stop_id") != payload["stop_id"]):
        _drop_from_stop(token, previous["kind"], previous["stop_id"])
    blob = json.dumps(payload, separators=(",", ":"))
    kv_set(f"{_SUB_PREFIX}{token}", blob, _TTL)
    set_add(_TOKENS_KEY, token)
    set_add(_STOPS_KEY, _stop_member(payload["kind"], payload["stop_id"]))
    set_add(_stop_tokens_key(payload["kind"], payload["stop_id"]), token)
    _memory[token] = payload


def unsubscribe(token: str) -> None:
    token = token.strip().lower()
    previous = _load_subscription(token)
    kv_delete(f"{_SUB_PREFIX}{token}")
    set_remove(_TOKENS_KEY, token)
    if previous:
        _drop_from_stop(token, previous["kind"], previous["stop_id"])
    _memory.pop(token, None)
    _last_fingerprint.pop(token, None)


def _load_subscription(token: str) -> dict | None:
    raw = kv_get(f"{_SUB_PREFIX}{token}")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return _memory.get(token)


def _subscriptions_for_stop(kind: str, stop_id: str) -> list[dict]:
    tokens = set_members(_stop_tokens_key(kind, stop_id))
    if not tokens:
        return [item for item in _memory.values() if item.get("kind") == kind and item.get("stop_id") == stop_id]
    found: list[dict] = []
    for token in tokens:
        payload = _load_subscription(token)
        if not payload:
            set_remove(_stop_tokens_key(kind, stop_id), token)
            set_remove(_TOKENS_KEY, token)
            continue
        found.append(payload)
    if not found:
        set_remove(_STOPS_KEY, _stop_member(kind, stop_id))
    return found


def _active_stops() -> list[tuple[str, str]]:
    members = set_members(_STOPS_KEY)
    if members:
        parsed = [_parse_stop_member(item) for item in members]
        return [item for item in parsed if item]
    seen: dict[tuple[str, str], None] = {}
    for payload in _memory.values():
        seen[(payload["kind"], payload["stop_id"])] = None
    return list(seen)


def _eta(minutes: int, now: float) -> float:
    if minutes <= 0:
        return now + 45
    return now + minutes * 60 + 59


def _stale_date(etas: list[float], now: float, online: bool) -> int:
    floor = now + (12 * 60 if online else 3 * 60)
    latest = max(etas) + 90 if etas else floor
    return int(max(latest, floor))


def bus_content_state(arrivals: LlegadasBus, preferred_line_id: str | None) -> tuple[dict, int]:
    now = time.time()
    proximos = arrivals.proximos
    if preferred_line_id:
        proximos = [item for item in proximos if item.linea.id == preferred_line_id]

    order: list[str] = []
    lines = {}
    minutes_by_line: dict[str, list[int]] = {}
    for proximo in proximos:
        line_id = proximo.linea.id
        if line_id not in minutes_by_line:
            order.append(line_id)
            lines[line_id] = proximo.linea
            minutes_by_line[line_id] = []
        minutes_by_line[line_id].append(proximo.minutos)

    rows = []
    etas: list[float] = []
    for line_id in order[:3]:
        times = sorted(minutes_by_line.get(line_id, []))[:3]
        if not times:
            continue
        linea = lines[line_id]
        first, rest = times[0], times[1:]
        first_eta = _eta(first, now)
        extra_etas = [_eta(value, now) for value in rest]
        etas.extend([first_eta, *extra_etas])
        rows.append(
            {
                "badge": linea.id,
                "colorHex": linea.color or "6b7280",
                "textColorHex": linea.text_color or "FFFFFF",
                "title": linea.id,
                "minutes": first,
                "eta": first_eta,
                "additionalMinutes": rest,
                "additionalETAs": extra_etas,
            }
        )

    state = {
        "stopName": arrivals.parada.nombre,
        "subtitle": f"Parada {arrivals.parada.id}",
        "kind": "bus",
        "rows": rows,
        "armillaMinutes": [],
        "alboloteMinutes": [],
        "armillaETAs": [],
        "alboloteETAs": [],
        "metroDirection": "Armilla",
        "metroInverted": False,
        "stopNumber": arrivals.parada.id,
        "updatedAt": now,
        "isOnline": True,
    }
    if preferred_line_id:
        state["preferredLineId"] = preferred_line_id
    return state, _stale_date(etas, now, True)


def metro_content_state(
    arrivals: LlegadasMetro,
    direction: str,
    inverted: bool,
) -> tuple[dict, int]:
    now = time.time()
    armilla = sorted(item.minutos for item in arrivals.proximos if item.direccion == DireccionMetro.Armilla)[:2]
    albolote = sorted(item.minutos for item in arrivals.proximos if item.direccion == DireccionMetro.Albolote)[:2]
    armilla_etas = [_eta(value, now) for value in armilla]
    albolote_etas = [_eta(value, now) for value in albolote]
    state = {
        "stopName": arrivals.parada.nombre,
        "subtitle": direction,
        "kind": "metro",
        "rows": [],
        "armillaMinutes": armilla,
        "alboloteMinutes": albolote,
        "armillaETAs": armilla_etas,
        "alboloteETAs": albolote_etas,
        "metroDirection": direction,
        "metroInverted": inverted,
        "updatedAt": now,
        "isOnline": True,
    }
    return state, _stale_date(armilla_etas + albolote_etas, now, True)


def _fingerprint(state: dict) -> str:
    payload = {key: value for key, value in state.items() if key not in {"updatedAt", "armillaETAs", "alboloteETAs"}}
    if "rows" in payload:
        payload["rows"] = [
            {key: value for key, value in row.items() if key not in {"eta", "additionalETAs"}}
            for row in payload["rows"]
        ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _variant_key(sub: dict) -> tuple:
    return (
        sub.get("preferred_line_id"),
        sub.get("metro_direction") or "Armilla",
        bool(sub.get("metro_inverted")),
    )


def _deliver(sub: dict, state: dict, stale: int, digest: str) -> None:
    token = sub["token"]
    status = send_live_update(token, sub["environment"], state, stale)
    if status in {200, 202}:
        _last_fingerprint[token] = digest
    elif status in {400, 403, 404, 410}:
        unsubscribe(token)


def _fanout(recips: list[dict], state: dict, stale: int) -> None:
    digest = _fingerprint(state)
    pending = [sub for sub in recips if _last_fingerprint.get(sub["token"]) != digest]
    if not pending:
        return
    if len(pending) == 1:
        _deliver(pending[0], state, stale, digest)
        return
    futures = [_apns_pool.submit(_deliver, sub, state, stale, digest) for sub in pending]
    for future in as_completed(futures):
        future.result()


def tick() -> None:
    if not is_configured():
        return
    if not try_lock("live:tick", _INTERVAL):
        return
    stops = _active_stops()
    if not stops:
        return

    metro_all: list[LlegadasMetro] | None = None
    if any(kind == "metro" for kind, _ in stops):
        try:
            metro_all = get_llegadas()
        except Exception:
            logger.exception("metro scrape failed")
            metro_all = []

    for kind, stop_id in stops:
        group = _subscriptions_for_stop(kind, stop_id)
        if not group:
            continue

        arrivals_bus: LlegadasBus | None = None
        arrivals_metro: LlegadasMetro | None = None
        try:
            if kind == "bus":
                arrivals_bus = get_llegadas_parada(int(stop_id))
            elif metro_all is not None:
                arrivals_metro = next((item for item in metro_all if item.parada.id == stop_id), None)
        except Exception:
            logger.exception("arrivals failed for %s %s", kind, stop_id)
            continue

        variants: dict[tuple, list[dict]] = defaultdict(list)
        for sub in group:
            variants[_variant_key(sub)].append(sub)

        for (preferred, direction, inverted), recips in variants.items():
            if kind == "bus" and arrivals_bus is not None:
                state, stale = bus_content_state(arrivals_bus, preferred)
            elif kind == "metro" and arrivals_metro is not None:
                state, stale = metro_content_state(arrivals_metro, direction, inverted)
            else:
                continue
            _fanout(recips, state, stale)


async def run_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(tick)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("live activity tick failed")
        await asyncio.sleep(_INTERVAL)
