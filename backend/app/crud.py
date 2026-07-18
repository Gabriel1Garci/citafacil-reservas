"""Operaciones de base de datos (Create/Read/Update/Delete)."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from . import models, schemas


# ---------- Servicios ----------
def list_services(db: Session, only_active: bool = True) -> list[models.Service]:
    q = db.query(models.Service)
    if only_active:
        q = q.filter(models.Service.active.is_(True))
    return q.order_by(models.Service.id).all()


def get_service(db: Session, service_id: int) -> Optional[models.Service]:
    return db.query(models.Service).filter(models.Service.id == service_id).first()


def create_service(db: Session, data: schemas.ServiceCreate) -> models.Service:
    obj = models.Service(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_service(db: Session, service: models.Service, data: schemas.ServiceUpdate) -> models.Service:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


def delete_service(db: Session, service: models.Service) -> None:
    db.delete(service)
    db.commit()


# ---------- Citas ----------
def create_appointment(
    db: Session, data: schemas.AppointmentCreate, service: models.Service, end_at: datetime
) -> models.Appointment:
    obj = models.Appointment(
        customer_name=data.customer_name.strip(),
        customer_phone=data.customer_phone,
        service_id=service.id,
        start_at=data.start_at,
        end_at=end_at,
        notes=(data.notes or "").strip(),
        status=models.STATUS_PENDING,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_appointments(
    db: Session, status: Optional[str] = None, day: Optional[date] = None
) -> list[models.Appointment]:
    q = db.query(models.Appointment)
    if status:
        q = q.filter(models.Appointment.status == status)
    if day:
        q = q.filter(
            models.Appointment.start_at >= datetime.combine(day, time.min),
            models.Appointment.start_at <= datetime.combine(day, time.max),
        )
    return q.order_by(models.Appointment.start_at).all()


def get_appointment(db: Session, appt_id: int) -> Optional[models.Appointment]:
    return db.query(models.Appointment).filter(models.Appointment.id == appt_id).first()


def set_status(db: Session, appt: models.Appointment, status: str) -> models.Appointment:
    appt.status = status
    db.commit()
    db.refresh(appt)
    return appt


def delete_appointment(db: Session, appt: models.Appointment) -> None:
    db.delete(appt)
    db.commit()


def stats(db: Session) -> dict:
    from .utils import local_now

    def count(status: str) -> int:
        return db.query(models.Appointment).filter(models.Appointment.status == status).count()

    upcoming = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.start_at >= local_now(),
            models.Appointment.status.in_([models.STATUS_PENDING, models.STATUS_CONFIRMED]),
        )
        .count()
    )
    return {
        "total": db.query(models.Appointment).count(),
        "pending": count(models.STATUS_PENDING),
        "confirmed": count(models.STATUS_CONFIRMED),
        "cancelled": count(models.STATUS_CANCELLED),
        "done": count(models.STATUS_DONE),
        "upcoming": upcoming,
    }
