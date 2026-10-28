"""Esquemas Pydantic (validación de entrada/salida de la API)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from .models import VALID_STATUSES
from .utils import PhoneError, normalize_cl_phone, to_local_naive


# ---------- Servicios ----------
class ServiceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    duration_min: int = Field(30, ge=5, le=480)
    price: int = Field(0, ge=0)
    active: bool = True


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    duration_min: Optional[int] = Field(None, ge=5, le=480)
    price: Optional[int] = Field(None, ge=0)
    active: Optional[bool] = None


class ServiceOut(ServiceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Pago ----------
class PaymentIn(BaseModel):
    """Datos de tarjeta que envía el formulario de pago (se validan y se descartan)."""

    holder: str = Field(..., min_length=2, max_length=80)
    card_number: SecretStr
    exp_month: int = Field(..., ge=1, le=12)
    exp_year: int = Field(..., ge=0, le=9999)
    cvv: SecretStr
    save: bool = Field(False, description="Guardar marca y últimos 4 para próximas reservas")


class PaymentSummary(BaseModel):
    brand: str
    last4: str
    exp_month: int
    exp_year: int


class CustomerOut(BaseModel):
    name: str
    phone: str
    payment: Optional[PaymentSummary] = None


# ---------- Citas ----------
class AppointmentCreate(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=120)
    customer_phone: str = Field(..., examples=["+56 9 4291 6570"])
    service_id: int
    start_at: datetime = Field(..., description="Inicio de la cita (ISO 8601)")
    notes: str = Field("", max_length=300)
    payment: Optional[PaymentIn] = None
    use_saved_payment: bool = Field(False, description="Cobrar a la tarjeta guardada (requiere X-Customer-Token)")

    @model_validator(mode="after")
    def _one_payment_source(self):
        if self.payment and self.use_saved_payment:
            raise ValueError("Usa tarjeta nueva o tarjeta guardada, no ambas.")
        return self

    @field_validator("customer_phone")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        try:
            return normalize_cl_phone(v)
        except PhoneError as e:
            raise ValueError(str(e))

    @field_validator("start_at")
    @classmethod
    def _naive_local(cls, v: datetime) -> datetime:
        return to_local_naive(v)


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_name: str
    customer_phone: str
    service_id: int
    start_at: datetime
    end_at: datetime
    status: str
    notes: str
    reminder_sent: bool
    cancel_code: Optional[str] = None
    payment_status: Optional[str] = None
    paid_amount: Optional[int] = None
    payment_last4: Optional[str] = None
    created_at: datetime
    service: Optional[ServiceOut] = None


class BookingOut(AppointmentOut):
    """Respuesta al reservar; `customer_token` solo viene cuando se creó un perfil."""

    customer_token: Optional[str] = None


class CancelRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=12, description="Código de cancelación")

    @field_validator("code")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return v.strip().upper()


class AppointmentStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"Estado inválido. Debe ser uno de: {sorted(VALID_STATUSES)}")
        return v


# ---------- Otros ----------
class ConfigOut(BaseModel):
    business_name: str
    timezone: str
    currency: str
    open_hour: int
    close_hour: int
    slot_interval_minutes: int
    closed_weekdays: list[int]


class StatsOut(BaseModel):
    total: int
    pending: int
    confirmed: int
    cancelled: int
    done: int
    upcoming: int


class CalendarDay(BaseModel):
    date: str
    status: str  # available | full | closed | past
    free_slots: int


class CalendarOut(BaseModel):
    month: str
    days: list[CalendarDay]


class MessageOut(BaseModel):
    detail: str
