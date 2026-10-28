"""US4: el cliente cancela su reserva con un código de cancelación."""
from datetime import timedelta

from app import models
from app.database import SessionLocal
from app.utils import local_now

from .helpers import client, next_open_day_at


def _book(start=None, phone="942916570"):
    sid = client.get("/api/services").json()[0]["id"]
    start = start or next_open_day_at(11, days=2)
    r = client.post(
        "/api/appointments",
        json={
            "customer_name": "Camila",
            "customer_phone": phone,
            "service_id": sid,
            "start_at": start.isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    return r.json(), sid, start


def test_booking_returns_cancel_code():
    appt, _, _ = _book()
    assert len(appt["cancel_code"]) == 8
    assert appt["cancel_code"].isalnum()


def test_cancel_code_is_unique_per_appointment():
    a, _, _ = _book()
    b, _, _ = _book(start=next_open_day_at(12, days=2), phone="911112222")
    assert a["cancel_code"] != b["cancel_code"]


def test_cancel_frees_the_slot():
    appt, sid, start = _book()
    r = client.post("/api/appointments/cancel", json={"code": appt["cancel_code"]})
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    slots = client.get(f"/api/availability?service_id={sid}&date={start.date().isoformat()}").json()
    assert start.strftime("%H:%M") in slots


def test_cancel_code_is_case_insensitive_and_trimmed():
    appt, _, _ = _book()
    r = client.post("/api/appointments/cancel", json={"code": "  " + appt["cancel_code"].lower() + " "})
    assert r.status_code == 200


def test_cancel_unknown_code_is_404():
    r = client.post("/api/appointments/cancel", json={"code": "ZZZZZZZZ"})
    assert r.status_code == 404
    assert "código" in r.json()["detail"].lower()  # error de la lógica, no ruta inexistente


def test_cancel_twice_is_409():
    appt, _, _ = _book()
    assert client.post("/api/appointments/cancel", json={"code": appt["cancel_code"]}).status_code == 200
    r = client.post("/api/appointments/cancel", json={"code": appt["cancel_code"]})
    assert r.status_code == 409


def test_cannot_cancel_past_appointment():
    appt, _, _ = _book()
    db = SessionLocal()
    row = db.query(models.Appointment).filter_by(id=appt["id"]).one()
    row.start_at = local_now() - timedelta(hours=2)
    row.end_at = row.start_at + timedelta(minutes=30)
    db.commit()
    db.close()
    r = client.post("/api/appointments/cancel", json={"code": appt["cancel_code"]})
    assert r.status_code == 409


def test_cancel_code_too_short_is_422():
    assert client.post("/api/appointments/cancel", json={"code": "ab"}).status_code == 422


def test_confirmation_message_includes_cancel_code():
    from datetime import datetime

    from app.notifications import confirmation_message

    body = confirmation_message("Negocio", "Ana", "Corte", datetime(2030, 1, 1, 10, 0), "ABCD2345")
    assert "ABCD2345" in body
