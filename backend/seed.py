"""Siembra datos de ejemplo (una barbería) para la demo.

Uso:  python seed.py
"""
from __future__ import annotations

from datetime import timedelta

from app import models
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.utils import local_now, normalize_cl_phone

SERVICES = [
    {"name": "Corte de pelo", "duration_min": 30, "price": 8000},
    {"name": "Corte + Barba", "duration_min": 45, "price": 12000},
    {"name": "Perfilado de barba", "duration_min": 20, "price": 6000},
    {"name": "Corte niño", "duration_min": 25, "price": 6500},
    {"name": "Tinte / Color", "duration_min": 60, "price": 18000},
]


def _next_open_day(hour: int):
    d = (local_now() + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)
    while d.weekday() in settings.closed_weekdays_set:
        d += timedelta(days=1)
    return d


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.Service).count() == 0:
            for s in SERVICES:
                db.add(models.Service(**s))
            db.commit()
            print(f"✔ Sembrados {len(SERVICES)} servicios.")
        else:
            print("• Ya existen servicios; no se vuelve a sembrar.")

        if db.query(models.Appointment).count() == 0:
            corte = db.query(models.Service).filter_by(name="Corte de pelo").first()
            barba = db.query(models.Service).filter_by(name="Corte + Barba").first()
            base = _next_open_day(11)
            ejemplos = [
                ("Camila Rojas", "+56 9 8765 4321", corte, base),
                ("Diego Soto", "+56 9 1234 5678", barba, base.replace(hour=12)),
            ]
            for name, phone, svc, start in ejemplos:
                db.add(
                    models.Appointment(
                        customer_name=name,
                        customer_phone=normalize_cl_phone(phone),
                        service_id=svc.id,
                        start_at=start,
                        end_at=start + timedelta(minutes=svc.duration_min),
                        status=models.STATUS_CONFIRMED,
                    )
                )
            db.commit()
            print("✔ Citas de ejemplo creadas.")
        else:
            print("• Ya existen citas; no se crean ejemplos.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
