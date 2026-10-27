"""US2: calendario dinámico de días disponibles y ocupados."""
from datetime import date, timedelta

from app.utils import local_now

from .helpers import client, next_open_day_at


def _sid():
    return client.get("/api/services").json()[0]["id"]


def _month(d):
    return d.strftime("%Y-%m")


def _by_date(payload):
    return {x["date"]: x for x in payload["days"]}


def _book(service_id, start, phone="942916570", name="Cliente"):
    return client.post(
        "/api/appointments",
        json={
            "customer_name": name,
            "customer_phone": phone,
            "service_id": service_id,
            "start_at": start.isoformat(),
        },
    )


def test_calendar_returns_every_day_of_month():
    today = local_now().date()
    r = client.get(f"/api/calendar?service_id={_sid()}&month={_month(today)}")
    assert r.status_code == 200
    body = r.json()
    assert body["month"] == _month(today)
    first = today.replace(day=1)
    next_first = (first + timedelta(days=32)).replace(day=1)
    assert len(body["days"]) == (next_first - first).days


def test_calendar_marks_past_closed_and_available():
    today = local_now().date()
    future = next_open_day_at(11, days=3).date()
    days = _by_date(client.get(f"/api/calendar?service_id={_sid()}&month={_month(future)}").json())
    assert days[future.isoformat()]["status"] == "available"
    assert days[future.isoformat()]["free_slots"] > 0
    sundays = [
        d for d in days.values()
        if date.fromisoformat(d["date"]).weekday() == 6 and date.fromisoformat(d["date"]) >= today
    ]
    if not sundays:  # fin de mes sin domingos futuros: probar el mes siguiente
        nxt = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        more = _by_date(client.get(f"/api/calendar?service_id={_sid()}&month={_month(nxt)}").json())
        sundays = [d for d in more.values() if date.fromisoformat(d["date"]).weekday() == 6]
    assert sundays and all(s["status"] == "closed" for s in sundays)
    yesterday = today - timedelta(days=1)
    if _month(yesterday) == _month(future):
        assert days[yesterday.isoformat()]["status"] == "past"


def test_calendar_marks_fully_booked_day_as_full():
    sid = _sid()
    day = next_open_day_at(10, days=2)
    # 10:00 a 19:30 en bloques de 30 min = 20 citas (distintos teléfonos)
    for i in range(20):
        start = day.replace(hour=10 + i // 2, minute=30 * (i % 2))
        assert _book(sid, start, phone=f"9{i:08d}"[:9], name=f"C{i}").status_code == 201
    days = _by_date(client.get(f"/api/calendar?service_id={sid}&month={_month(day)}").json())
    assert days[day.date().isoformat()]["status"] == "full"
    assert days[day.date().isoformat()]["free_slots"] == 0


def test_calendar_day_with_one_booking_stays_available():
    sid = _sid()
    day = next_open_day_at(11, days=2)
    _book(sid, day)
    days = _by_date(client.get(f"/api/calendar?service_id={sid}&month={_month(day)}").json())
    # un día con 1 cita sigue disponible pero con una hora menos
    assert days[day.date().isoformat()]["status"] == "available"


def test_calendar_validation():
    sid = _sid()
    assert client.get(f"/api/calendar?service_id={sid}&month=2026-13").status_code == 422
    assert client.get(f"/api/calendar?service_id={sid}&month=abril").status_code == 422
    assert client.get("/api/calendar?service_id=9999&month=2026-05").status_code == 404
