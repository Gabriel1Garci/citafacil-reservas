"""Recordatorios automáticos de citas por WhatsApp."""
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import SessionLocal
from .notifications import reminder_message, send_whatsapp
from .utils import local_now

logger = logging.getLogger("citafacil.reminders")


def run_reminders(db: Session) -> dict:
    """Busca citas próximas sin recordatorio y las notifica por WhatsApp."""
    now = local_now()
    horizon = now + timedelta(hours=settings.reminder_hours_before)

    citas = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.reminder_sent.is_(False),
            models.Appointment.status.in_([models.STATUS_PENDING, models.STATUS_CONFIRMED]),
            models.Appointment.start_at > now,
            models.Appointment.start_at <= horizon,
        )
        .all()
    )

    enviados = 0
    for cita in citas:
        service_name = cita.service.name if cita.service else "tu servicio"
        body = reminder_message(settings.business_name, cita.customer_name, service_name, cita.start_at)
        result = send_whatsapp(cita.customer_phone, body)
        if result.get("ok"):
            cita.reminder_sent = True
            enviados += 1
    db.commit()

    logger.info("Recordatorios: %s enviados de %s candidatas.", enviados, len(citas))
    return {"candidatas": len(citas), "enviados": enviados}


def run_reminders_job() -> None:
    """Wrapper para el programador (APScheduler): abre y cierra su propia sesión."""
    db = SessionLocal()
    try:
        run_reminders(db)
    finally:
        db.close()
