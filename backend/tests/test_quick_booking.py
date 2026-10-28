"""US1: reserva rápida con datos de pago guardados."""
from sqlalchemy import text

from app.database import engine

from .helpers import ADMIN, client, next_open_day_at

CARD = {
    "holder": "Camila Rojas",
    "card_number": "4242 4242 4242 4242",
    "exp_month": 12,
    "exp_year": 2099,
    "cvv": "123",
}


def _sid():
    return client.get("/api/services").json()[0]["id"]


def _payload(hour=11, days=2, payment=None, **extra):
    body = {
        "customer_name": "Camila Rojas",
        "customer_phone": "+56 9 8765 4321",
        "service_id": _sid(),
        "start_at": next_open_day_at(hour, days=days).isoformat(),
        **extra,
    }
    if payment is not None:
        body["payment"] = payment
    return body


def _admin_count():
    return len(client.get("/api/admin/appointments", headers=ADMIN).json())


def test_booking_with_payment_is_paid_and_hides_card_data():
    r = client.post("/api/appointments", json=_payload(payment=CARD))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["payment_status"] == "paid"
    assert body["payment_last4"] == "4242"
    assert body["paid_amount"] == 8000
    assert "4242424242424242" not in r.text.replace(" ", "")
    assert "cvv" not in r.text.lower()
    assert body.get("customer_token") is None  # no pidió guardar


def test_booking_without_payment_stays_unpaid_for_backward_compatibility():
    r = client.post("/api/appointments", json=_payload())
    assert r.status_code == 201
    assert r.json()["payment_status"] == "unpaid"


def test_declined_card_returns_402_and_creates_no_appointment():
    bad = {**CARD, "card_number": "4000 0000 0000 0002"}
    r = client.post("/api/appointments", json=_payload(payment=bad))
    assert r.status_code == 402
    assert _admin_count() == 0


def test_expired_card_is_rejected_with_422():
    r = client.post("/api/appointments", json=_payload(payment={**CARD, "exp_year": 2020}))
    assert r.status_code == 422
    assert _admin_count() == 0


def test_save_returns_customer_token_and_profile_shows_masked_card():
    r = client.post("/api/appointments", json=_payload(payment={**CARD, "save": True}))
    assert r.status_code == 201, r.text
    token = r.json()["customer_token"]
    assert token and len(token) >= 32

    me = client.get("/api/customers/me", headers={"X-Customer-Token": token})
    assert me.status_code == 200
    data = me.json()
    assert data["name"] == "Camila Rojas"
    assert data["phone"] == "+56987654321"
    assert data["payment"] == {"brand": "visa", "last4": "4242", "exp_month": 12, "exp_year": 2099}
    assert "4242424242424242" not in me.text


def test_profile_requires_a_valid_token_and_not_just_a_phone():
    client.post("/api/appointments", json=_payload(payment={**CARD, "save": True}))
    assert client.get("/api/customers/me").status_code == 401
    assert client.get("/api/customers/me", headers={"X-Customer-Token": "x" * 40}).status_code == 401
    assert client.get("/api/customers/lookup?phone=%2B56987654321").status_code == 404  # no hay búsqueda por teléfono


def test_quick_booking_with_saved_payment_needs_no_card():
    token = client.post("/api/appointments", json=_payload(payment={**CARD, "save": True})).json()["customer_token"]
    r = client.post(
        "/api/appointments",
        json=_payload(hour=13, use_saved_payment=True),
        headers={"X-Customer-Token": token},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["payment_status"] == "paid" and body["payment_last4"] == "4242"
    assert body.get("customer_token") is None  # el token no se vuelve a emitir


def test_quick_booking_without_valid_token_is_401_and_creates_nothing():
    before = _admin_count()
    r = client.post("/api/appointments", json=_payload(use_saved_payment=True))
    assert r.status_code == 401
    r = client.post(
        "/api/appointments",
        json=_payload(use_saved_payment=True),
        headers={"X-Customer-Token": "y" * 40},
    )
    assert r.status_code == 401
    assert _admin_count() == before


def test_forget_my_data_deletes_profile_and_token_stops_working():
    token = client.post("/api/appointments", json=_payload(payment={**CARD, "save": True})).json()["customer_token"]
    h = {"X-Customer-Token": token}
    assert client.delete("/api/customers/me", headers=h).status_code == 200
    assert client.get("/api/customers/me", headers=h).status_code == 401
    r = client.post("/api/appointments", json=_payload(hour=15, use_saved_payment=True), headers=h)
    assert r.status_code == 401


def test_full_card_number_and_cvv_are_never_stored():
    client.post("/api/appointments", json=_payload(payment={**CARD, "save": True}))
    values = []
    with engine.connect() as conn:
        for table in ("customers", "payment_methods", "appointments"):
            for row in conn.execute(text(f"SELECT * FROM {table}")):
                values.extend(str(v) for v in row)
    assert not any("4242424242424242" in v.replace(" ", "") for v in values)
    assert "123" not in values  # el CVV no aparece como valor de ninguna columna
    assert "4242" in values  # solo se guardan los últimos 4


def test_validation_errors_never_echo_card_data():
    """Regresión: el 422 de FastAPI incluye `input`; no debe reenviar tarjeta ni CVV."""
    both = client.post("/api/appointments", json=_payload(payment=CARD, use_saved_payment=True))
    assert both.status_code == 422
    bad_month = client.post("/api/appointments", json=_payload(payment={**CARD, "exp_month": 13}))
    assert bad_month.status_code == 422
    for r in (both, bad_month):
        flat = r.text.replace(" ", "")
        assert "4242424242424242" not in flat
        assert '"cvv"' not in r.text and "123" not in r.text
