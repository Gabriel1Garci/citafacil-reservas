"""Siembra ~12 semanas de HISTORIAL de reservas para probar la previsión de demanda.

Genera un patrón realista y reproducible: más demanda viernes y sábado, menos a
inicio de semana, y un leve crecimiento en las últimas 4 semanas.

Uso:  python seed_history.py
"""
from __future__ import annotations

import random
from datetime import datetime, time, timedelta

from app import models
from app.config import settings
from app.database import SessionLocal, ensure_schema
from app.utils import local_now

# Ocupación base por día de la semana (0=lunes ... 6=domingo)
WEIGHTS = {0: 0.30, 1: 0.35, 2: 0.45, 3: 0.55, 4: 0.85, 5: 0.95, 6: 0.0}
NAMES = ["Camila", "Diego", "Sofia", "Mateo", "Valentina", "Benjamin", "Isidora", "Tomas", "Fernanda", "Joaquin"]
HISTORY_WEEKS = 12


def run() -> None:
    ensure_schema()
    db = SessionLocal()
    try:
        service = db.query(models.Service).order_by(models.Service.id).first()
        if service is None:
            print("Primero ejecuta seed.py para crear los servicios.")
            return
        now = local_now()
        already = db.query(models.Appointment).filter(models.Appointment.start_at < now).count()
        if already > 10:
            print(f"Ya hay {already} citas pasadas; no se siembra historial.")
            return

        rng = random.Random(42)  # reproducible
        capacity = (settings.close_hour - settings.open_hour) * 60 // settings.slot_interval_minutes
        start_day = now.date() - timedelta(weeks=HISTORY_WEEKS)
        created = 0
        day = start_day
        while day < now.date():
            weight = WEIGHTS[day.weekday()]
            if day.weekday() not in settings.closed_weekdays_set and weight > 0:
                growth = 1.15 if day >= now.date() - timedelta(weeks=4) else 1.0
                n = int(round(capacity * weight * growth + rng.randint(-2, 2)))
                n = max(0, min(n, capacity))
                slots = sorted(rng.sample(range(capacity), n))
                for idx in slots:
                    start = datetime.combine(day, time(settings.open_hour)) + timedelta(
                        minutes=idx * settings.slot_interval_minutes
                    )
                    db.add(models.Appointment(
                        customer_name=f"{rng.choice(NAMES)} (historial)",
                        customer_phone="+56900000000",
                        service_id=service.id,
                        start_at=start,
                        end_at=start + timedelta(minutes=service.duration_min),
                        status=models.STATUS_DONE,
                    ))
                    created += 1
            day += timedelta(days=1)
        db.commit()
        print(f"OK: {created} citas historicas creadas en {HISTORY_WEEKS} semanas.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
