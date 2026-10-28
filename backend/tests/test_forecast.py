"""US3: previsión de demanda para el administrador."""
from datetime import date, datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal
from app.forecast import build_forecast
from app.utils import local_now

from .helpers import ADMIN, client

TODAY = date(2026, 6, 10)  # miércoles
CLOSED = {6}


def _mondays_back(n, count):
    """Citas `count` por lunes durante las últimas n semanas."""
    out = {}
    d = TODAY - timedelta(days=1)
    while d >= TODAY - timedelta(weeks=n):
        if d.weekday() == 0:
            out[d] = count
        d -= timedelta(days=1)
    return out


def _forecast(counts, **kw):
    return build_forecast(
        counts, today=TODAY, horizon_days=kw.pop("horizon_days", 14),
        history_weeks=12, capacity=kw.pop("capacity", 20), closed_weekdays=CLOSED, **kw,
    )


def _by_date(result):
    return {f["date"]: f for f in result["forecast"]}


def test_forecast_has_requested_horizon_and_history_shapes():
    r = _forecast({})
    assert len(r["forecast"]) == 14
    assert len(r["history_weekly"]) == 12
    assert len(r["by_weekday"]) == 7
    assert r["forecast"][0]["date"] == (TODAY + timedelta(days=1)).isoformat()


def test_seasonal_mean_predicts_the_weekday_pattern():
    r = _forecast(_mondays_back(12, 8))
    days = _by_date(r)
    next_monday = TODAY + timedelta(days=(7 - TODAY.weekday()))
    assert days[next_monday.isoformat()]["expected"] == pytest.approx(8, abs=0.6)
    tuesday = (next_monday + timedelta(days=1)).isoformat()
    assert days[tuesday]["expected"] == 0


def test_closed_weekday_has_zero_demand_and_closed_level():
    r = _forecast(_mondays_back(12, 8))
    sundays = [f for f in r["forecast"] if date.fromisoformat(f["date"]).weekday() == 6]
    assert sundays
    assert all(f["expected"] == 0 and f["level"] == "closed" and f["price_change_pct"] == 0 for f in sundays)


def test_growing_trend_raises_forecast_and_is_clamped():
    flat = _mondays_back(12, 6)
    growing = dict(flat)
    for d in list(growing):
        if d >= TODAY - timedelta(weeks=4):
            growing[d] = 18  # triplica las últimas 4 semanas
    base = _forecast(flat)
    up = _forecast(growing)
    assert base["trend_factor"] == pytest.approx(1.0)
    assert up["trend_factor"] == pytest.approx(1.3)  # tope superior
    nm = (TODAY + timedelta(days=(7 - TODAY.weekday()))).isoformat()
    assert _by_date(up)[nm]["expected"] > _by_date(base)[nm]["expected"]


def test_levels_and_price_suggestions():
    high = _forecast(_mondays_back(12, 18))
    low = _forecast(_mondays_back(12, 2))
    nm = (TODAY + timedelta(days=(7 - TODAY.weekday()))).isoformat()
    assert _by_date(high)[nm]["level"] == "high" and _by_date(high)[nm]["price_change_pct"] == 10
    assert _by_date(low)[nm]["level"] == "low" and _by_date(low)[nm]["price_change_pct"] == -10
    mid = _forecast(_mondays_back(12, 10))
    assert _by_date(mid)[nm]["level"] == "normal" and _by_date(mid)[nm]["price_change_pct"] == 0


def test_already_booked_future_appointments_floor_the_forecast():
    tomorrow = TODAY + timedelta(days=1)
    r = _forecast({tomorrow: 15})
    assert _by_date(r)[tomorrow.isoformat()]["expected"] >= 15
    assert _by_date(r)[tomorrow.isoformat()]["booked"] == 15


def test_history_weekly_counts_are_correct_and_current_week_is_partial():
    r = _forecast(_mondays_back(12, 3))
    assert sum(w["count"] for w in r["history_weekly"]) == 3 * len(_mondays_back(12, 3))
    assert r["history_weekly"][-1]["partial"] is True
    assert all(w["partial"] is False for w in r["history_weekly"][:-1])


def test_recommendations_are_generated():
    r = _forecast(_mondays_back(12, 18))
    assert r["recommendations"] and all(isinstance(x, str) for x in r["recommendations"])


# ---------- API ----------
def _add_appt(day: datetime, status=models.STATUS_DONE, minutes=30):
    db = SessionLocal()
    db.add(models.Appointment(
        customer_name="Hist", customer_phone="+56911112222", service_id=1,
        start_at=day, end_at=day + timedelta(minutes=minutes), status=status,
    ))
    db.commit()
    db.close()


def test_forecast_endpoint_requires_admin_token():
    assert client.get("/api/admin/forecast").status_code == 422
    assert client.get("/api/admin/forecast", headers={"X-Admin-Token": "malo"}).status_code == 401


def test_forecast_endpoint_uses_history_and_ignores_cancelled():
    base = (local_now() - timedelta(days=7)).replace(hour=11, minute=0, second=0, microsecond=0)
    for i in range(3):
        _add_appt(base + timedelta(minutes=30 * i))
    _add_appt(base + timedelta(hours=5), status=models.STATUS_CANCELLED)
    r = client.get("/api/admin/forecast", headers=ADMIN)
    assert r.status_code == 200, r.text
    body = r.json()
    assert sum(w["count"] for w in body["history_weekly"]) == 3  # la cancelada no cuenta
    assert len(body["forecast"]) == 14


def test_forecast_endpoint_validates_days():
    assert client.get("/api/admin/forecast?days=0", headers=ADMIN).status_code == 422
    assert client.get("/api/admin/forecast?days=91", headers=ADMIN).status_code == 422
    assert len(client.get("/api/admin/forecast?days=7", headers=ADMIN).json()["forecast"]) == 7


def test_expected_never_exceeds_daily_capacity():
    # media ~17.7 x tendencia 1.3 = ~23 sin tope; la capacidad es 20
    counts = _mondays_back(12, 18)
    for d in list(counts):
        if d >= TODAY - timedelta(weeks=4):
            counts[d] = 20
        elif d >= TODAY - timedelta(weeks=8):
            counts[d] = 15
    r = _forecast(counts, capacity=20)
    nm = (TODAY + timedelta(days=(7 - TODAY.weekday()))).isoformat()
    assert r["trend_factor"] == pytest.approx(1.3)
    assert all(f["expected"] <= 20 for f in r["forecast"])
    assert _by_date(r)[nm]["expected"] == 20 and _by_date(r)[nm]["utilization"] == 1.0
