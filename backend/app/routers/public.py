"""Endpoints públicos: config, servicios, disponibilidad y creación de reservas."""
from __future__ import annotations

from datetime import date, timedelta

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..availability import generate_slots, is_slot_free, month_calendar
from ..config import settings
from ..database import get_db
from ..notifications import confirmation_message, send_whatsapp
from ..payments import CardInfo, PaymentDeclined, PaymentError, charge, ensure_not_expired, validate_card
from ..utils import local_now

router = APIRouter(prefix="/api", tags=["Público"])


@router.get("/config", response_model=schemas.ConfigOut, summary="Configuración del negocio")
def get_config():
    return schemas.ConfigOut(
        business_name=settings.business_name,
        timezone=settings.business_timezone,
        currency=settings.currency,
        open_hour=settings.open_hour,
        close_hour=settings.close_hour,
        slot_interval_minutes=settings.slot_interval_minutes,
        closed_weekdays=sorted(settings.closed_weekdays_set),
    )


@router.get("/services", response_model=list[schemas.ServiceOut], summary="Servicios activos")
def get_services(db: Session = Depends(get_db)):
    return crud.list_services(db, only_active=True)


@router.get("/availability", response_model=list[str], summary="Horarios disponibles")
def get_availability(
    service_id: int = Query(..., description="ID del servicio"),
    day: date = Query(..., alias="date", description="Fecha en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    service = crud.get_service(db, service_id)
    if not service or not service.active:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    return generate_slots(db, service, day)


@router.get("/calendar", response_model=schemas.CalendarOut, summary="Calendario mensual")
def get_calendar(
    service_id: int = Query(..., description="ID del servicio"),
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Mes YYYY-MM"),
    db: Session = Depends(get_db),
):
    service = crud.get_service(db, service_id)
    if not service or not service.active:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    year, mon = int(month[:4]), int(month[5:])
    return schemas.CalendarOut(month=month, days=month_calendar(db, service, year, mon))


@router.post(
    "/appointments",
    response_model=schemas.BookingOut,
    status_code=201,
    summary="Crear una reserva (con pago opcional)",
)
def create_appointment(
    payload: schemas.AppointmentCreate,
    db: Session = Depends(get_db),
    x_customer_token: Optional[str] = Header(None, alias="X-Customer-Token"),
):
    service = crud.get_service(db, payload.service_id)
    if not service or not service.active:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    if not is_slot_free(db, service, payload.start_at):
        raise HTTPException(
            status_code=409,
            detail="Ese horario ya no está disponible. Por favor elige otro.",
        )
    end_at = payload.start_at + timedelta(minutes=service.duration_min)

    # --- Pago: tarjeta nueva, tarjeta guardada o sin pago (retrocompatible) ---
    customer = None
    card: Optional[CardInfo] = None
    if payload.use_saved_payment:
        customer = crud.get_customer_by_token(db, x_customer_token)
        if not customer or not customer.payment:
            raise HTTPException(status_code=401, detail="No encontramos tus datos guardados.")
        pm = customer.payment
        card = CardInfo(pm.brand, pm.last4, pm.exp_month, pm.exp_year)
        try:
            ensure_not_expired(card)
        except PaymentError as e:
            raise HTTPException(status_code=422, detail=str(e))
    elif payload.payment:
        p = payload.payment
        try:
            card = validate_card(
                p.card_number.get_secret_value(), p.exp_month, p.exp_year, p.cvv.get_secret_value()
            )
        except PaymentError as e:
            raise HTTPException(status_code=422, detail=str(e))

    payment_status, paid_amount, last4 = models.PAYMENT_UNPAID, None, None
    if card:
        if service.price <= 0:
            payment_status, paid_amount, last4 = models.PAYMENT_FREE, 0, card.last4
        else:
            try:
                charge(card, service.price)
            except PaymentDeclined as e:
                raise HTTPException(status_code=402, detail=str(e))
            except PaymentError as e:
                raise HTTPException(status_code=422, detail=str(e))
            payment_status, paid_amount, last4 = models.PAYMENT_PAID, service.price, card.last4

    token = None
    if card and payload.payment and payload.payment.save:
        customer, token = crud.create_customer(
            db, payload.customer_name, payload.customer_phone, payload.payment.holder, card
        )

    appt = crud.create_appointment(
        db, payload, service, end_at,
        customer=customer, payment_status=payment_status, paid_amount=paid_amount, payment_last4=last4,
    )

    # Confirmación por WhatsApp (real si Twilio está configurado; simulada si no)
    body = confirmation_message(
        settings.business_name, appt.customer_name, service.name, appt.start_at, appt.cancel_code
    )
    send_whatsapp(appt.customer_phone, body)
    result = schemas.BookingOut.model_validate(appt)
    result.customer_token = token
    return result


@router.post(
    "/appointments/cancel",
    response_model=schemas.AppointmentOut,
    summary="Cancelar una reserva con su código",
)
def cancel_appointment(payload: schemas.CancelRequest, db: Session = Depends(get_db)):
    appt = crud.get_by_cancel_code(db, payload.code)
    if not appt:
        raise HTTPException(status_code=404, detail="Código de cancelación no válido.")
    if appt.status == models.STATUS_CANCELLED:
        raise HTTPException(status_code=409, detail="Esta reserva ya estaba cancelada.")
    if appt.status == models.STATUS_DONE or appt.start_at <= local_now():
        raise HTTPException(status_code=409, detail="No se puede cancelar una cita que ya pasó.")
    return crud.set_status(db, appt, models.STATUS_CANCELLED)
