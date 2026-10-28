"""US5: exportar reservas a CSV (con filtros y protección contra inyección de fórmulas)."""
import csv
import io

from .helpers import ADMIN, client, next_open_day_at


def _book(hour, name="Camila Rojas", phone="942916570", notes="", days=2):
    sid = client.get("/api/services").json()[0]["id"]
    r = client.post("/api/appointments", json={
        "customer_name": name, "customer_phone": phone, "service_id": sid,
        "start_at": next_open_day_at(hour, days=days).isoformat(), "notes": notes,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _export(query=""):
    r = client.get("/api/admin/appointments/export.csv" + query, headers=ADMIN)
    assert r.status_code == 200, r.text
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    return r, rows


def test_export_requires_admin_token():
    assert client.get("/api/admin/appointments/export.csv").status_code == 422
    assert client.get("/api/admin/appointments/export.csv", headers={"X-Admin-Token": "malo"}).status_code == 401


def test_export_headers_and_encoding():
    _book(11, name="José Núñez")
    r, rows = _export()
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and ".csv" in r.headers["content-disposition"]
    assert r.content.startswith(b"\xef\xbb\xbf")  # BOM: Excel abre bien los acentos
    assert rows[0][:4] == ["ID", "Fecha", "Hora", "Cliente"]
    assert any(row[3] == "José Núñez" for row in rows[1:])


def test_export_has_one_row_per_appointment_with_price_and_payment():
    _book(11)
    _book(12, phone="911112222")
    _, rows = _export()
    assert len(rows) == 3  # cabecera + 2
    header = rows[0]
    row = dict(zip(header, rows[1]))
    assert row["Precio"] == "8000" and row["Estado"] == "pending" and row["Pago"] == "unpaid"


def test_export_respects_status_filter():
    a = _book(11)
    _book(12, phone="911112222")
    client.patch(f"/api/admin/appointments/{a['id']}", json={"status": "confirmed"}, headers=ADMIN)
    _, rows = _export("?status=confirmed")
    assert len(rows) == 2 and rows[1][0] == str(a["id"])


def test_export_respects_date_filter():
    _book(11, days=2)
    other = _book(12, phone="911112222", days=3)
    day = other["start_at"][:10]
    _, rows = _export(f"?date={day}")
    assert len(rows) == 2 and rows[1][0] == str(other["id"])


def test_export_neutralizes_formula_injection():
    _book(11, name="=HYPERLINK(\"http://x\",\"clic\")", notes="@SUM(1+1)")
    _book(12, phone="911112222", name="+cmd|' /C calc'!A0", notes="-2+3")
    _, rows = _export()
    header = rows[0]
    for r in rows[1:]:
        d = dict(zip(header, r))
        for col in ("Cliente", "Notas"):
            assert not d[col].startswith(("=", "+", "-", "@")), (col, d[col])
    names = [dict(zip(header, r))["Cliente"] for r in rows[1:]]
    assert "'=HYPERLINK(\"http://x\",\"clic\")" in names


def test_export_keeps_phone_readable():
    _book(11)
    _, rows = _export()
    assert dict(zip(rows[0], rows[1]))["Teléfono"] == "+56942916570"


def test_export_empty_has_only_header():
    _, rows = _export("?status=done")
    assert len(rows) == 1


def test_cors_exposes_content_disposition_so_the_browser_can_read_the_filename():
    r = client.get(
        "/api/admin/appointments/export.csv",
        headers={**ADMIN, "Origin": "http://localhost:5500"},
    )
    exposed = r.headers.get("access-control-expose-headers", "").lower()
    assert "content-disposition" in exposed
