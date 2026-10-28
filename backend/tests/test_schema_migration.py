"""Migración ligera: agrega columnas nuevas a tablas existentes sin perder datos."""
from sqlalchemy import create_engine, inspect, text

from app.database import ensure_schema


def test_ensure_schema_adds_missing_column_and_keeps_rows(tmp_path):
    eng = create_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    with eng.begin() as c:
        c.execute(text("CREATE TABLE services (id INTEGER PRIMARY KEY, name VARCHAR(120) NOT NULL, duration_min INTEGER NOT NULL, price INTEGER NOT NULL, active BOOLEAN NOT NULL)"))
        c.execute(text(
            "CREATE TABLE appointments (id INTEGER PRIMARY KEY, customer_name VARCHAR(120) NOT NULL,"
            " customer_phone VARCHAR(20) NOT NULL, service_id INTEGER NOT NULL, start_at DATETIME NOT NULL,"
            " end_at DATETIME NOT NULL, status VARCHAR(20) NOT NULL, notes VARCHAR(300) NOT NULL,"
            " reminder_sent BOOLEAN NOT NULL, created_at DATETIME NOT NULL)"
        ))
        c.execute(text("INSERT INTO services VALUES (1,'Corte',30,8000,1)"))
        c.execute(text(
            "INSERT INTO appointments VALUES (1,'Ana','+56911112222',1,'2030-01-01 10:00:00',"
            "'2030-01-01 10:30:00','pending','',0,'2029-12-01 00:00:00')"
        ))

    ensure_schema(bind=eng)
    ensure_schema(bind=eng)  # idempotente

    cols = {c["name"] for c in inspect(eng).get_columns("appointments")}
    assert "cancel_code" in cols
    with eng.connect() as c:
        assert tuple(c.execute(text("SELECT customer_name, cancel_code FROM appointments")).one()) == ("Ana", None)
