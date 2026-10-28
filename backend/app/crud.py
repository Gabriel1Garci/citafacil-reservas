"""Operaciones de base de datos (Create/Read/Update/Delete)."""
from __future__ import annotations

import hashlib
import secrets
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
# Sin caracteres ambiguos (0/O, 1/I/L) para que el código sea fácil de dictar.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def new_cancel_code(db: Session, length: int = 8) -> str:
    """Código aleatorio criptográficamente seguro y único."""
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))
        if not db.query(models.Appointment).filter_by(cancel_code=code).first():
            return code


def get_by_cancel_code(db: Session, code: str) -> Optional[models.Appointment]:
    return db.query(models.Appointment).filter(models.Appointment.cancel_code == code).first()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_customer(db: Session, name: str, phone: str, holder: str, card) -> tuple[models.Customer, str]:
    """Crea el perfil con su tarjeta (solo datos no sensibles). Devuelve (perfil, token en claro)."""
    token = secrets.token_urlsafe(32)
    customer = models.Customer(name=name.strip(), phone=phone, token_hash=_hash_token(token))
    customer.payment = models.PaymentMethod(
        holder=holder.strip(), brand=card.brand, last4=card.last4,
        exp_month=card.exp_month, exp_year=card.exp_year,
    )
    db.add(customer)
    db.flush()
    return customer, token


def get_customer_by_token(db: Session, token: Optional[str]) -> Optional[models.Customer]:
    if not token:
        return None
    return db.query(models.Customer).filter(models.Customer.token_hash == _hash_token(token)).first()


def delete_customer(db: Session, customer: models.Customer) -> None:
    """Olvida los datos guardados; las citas se conservan sin vínculo al perfil."""
    db.query(models.Appointment).filter(models.Appointment.customer_id == customer.id).update(
        {models.Appointment.customer_id: None}
    )
    db.delete(customer)
    db.commit()


def create_appointment(
    db: Session,
    data: schemas.AppointmentCreate,
    service: models.Service,
    end_at: datetime,
    customer: Optional[models.Customer] = None,
    payment_status: str = models.PAYMENT_UNPAID,
    paid_amount: Optional[int] = None,
    payment_last4: Optional[str] = None,
) -> models.Appointment:
    obj = models.Appointment(
        customer_name=data.customer_name.strip(),
        customer_phone=data.customer_phone,
        service_id=service.id,
        start_at=data.start_at,
        end_at=end_at,
        notes=(data.notes or "").strip(),
        status=models.STATUS_PENDING,
        cancel_code=new_cancel_code(db),
        customer_id=customer.id if customer else None,
        payment_status=payment_status,
        paid_amount=paid_amount,
        payment_last4=payment_last4,
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
