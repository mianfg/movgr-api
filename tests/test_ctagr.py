from datetime import datetime
from zoneinfo import ZoneInfo

from src.models.ctagr import LineaCtagr, LlegadasCtagr, ParadaCtagr, ProximoCtagr
from src.services.ctagr import _minutes_until
from src.services.live_activity import ctagr_content_state


def test_minutes_until_same_hour():
    now = datetime(2026, 9, 22, 17, 40, tzinfo=ZoneInfo("Europe/Madrid"))
    assert _minutes_until("17:48", now) == 8


def test_minutes_until_wraps_midnight():
    now = datetime(2026, 9, 22, 23, 50, tzinfo=ZoneInfo("Europe/Madrid"))
    assert _minutes_until("00:10", now) == 20


def test_ctagr_content_state_marks_live():
    arrivals = LlegadasCtagr(
        parada=ParadaCtagr(id="0124", nombre="Armilla"),
        proximos=[
            ProximoCtagr(
                linea=LineaCtagr(id="245", color="FFFFFF", text_color="15803d"),
                destino="Granada",
                hora="17:50",
                minutos=10,
                en_ruta=True,
            ),
            ProximoCtagr(
                linea=LineaCtagr(id="245", color="FFFFFF", text_color="15803d"),
                destino="Granada",
                hora="18:20",
                minutos=40,
                en_ruta=False,
            ),
        ],
    )
    state, _ = ctagr_content_state(arrivals, None)
    assert state["kind"] == "ctagr"
    assert state["subtitle"] == "Consorcio · en ruta"
    assert state["rows"][0]["badge"] == "245"
    assert "en ruta" in state["rows"][0]["title"]
    assert "stopNumber" not in state

