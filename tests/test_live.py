from src.models.bus import LineaBus, LlegadasBus, ParadaBus, ProximoBus
from src.models.live import LiveSubscribeRequest
from src.services import live_activity
from src.services.live_activity import _active_stops, _fingerprint, bus_content_state, subscribe, unsubscribe


def test_bus_content_state_groups_lines():
    arrivals = LlegadasBus(
        parada=ParadaBus(id=1503, nombre="Fuentenueva"),
        proximos=[
            ProximoBus(linea=LineaBus(id="4", color="cc0000", text_color="FFFFFF"), destino="Zaidin", minutos=4),
            ProximoBus(linea=LineaBus(id="4", color="cc0000", text_color="FFFFFF"), destino="Zaidin", minutos=11),
            ProximoBus(linea=LineaBus(id="5", color="000000"), destino="Otro", minutos=7),
        ],
    )
    state, stale = bus_content_state(arrivals, None)
    assert state["kind"] == "bus"
    assert len(state["rows"]) == 2
    assert state["rows"][0]["minutes"] == 4
    assert state["rows"][0]["additionalMinutes"] == [11]
    assert stale > state["updatedAt"]
    filtered, _ = bus_content_state(arrivals, "4")
    assert len(filtered["rows"]) == 1
    assert _fingerprint(state) != _fingerprint(filtered)


def test_subscriptions_index_by_stop_not_by_consumer():
    live_activity._memory.clear()
    subscribe(
        LiveSubscribeRequest(
            token="aa" * 32,
            environment="sandbox",
            kind="bus",
            stop_id="9901503",
        )
    )
    subscribe(
        LiveSubscribeRequest(
            token="bb" * 32,
            environment="sandbox",
            kind="bus",
            stop_id="9901503",
            preferred_line_id="4",
        )
    )
    subscribe(
        LiveSubscribeRequest(
            token="cc" * 32,
            environment="sandbox",
            kind="bus",
            stop_id="9901884",
        )
    )
    stops = set(_active_stops())
    assert ("bus", "9901503") in stops
    assert ("bus", "9901884") in stops
    group = live_activity._subscriptions_for_stop("bus", "9901503")
    assert {"aa" * 32, "bb" * 32} <= {item["token"] for item in group}
    unsubscribe("aa" * 32)
    unsubscribe("bb" * 32)
    unsubscribe("cc" * 32)
