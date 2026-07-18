"""Esquemas Pydantic (validación de entrada/salida de la API)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


# ---------- Citas ----------
class AppointmentCreate(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=120)
    customer_phone: str = Field(..., examples=["+56 9 4291 6570"])
    service_id: int
    start_at: datetime = Field(..., description="Inicio de la cita (ISO 8601)")
    notes: str = Field("", max_length=300)

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
    created_at: datetime
    service: Optional[ServiceOut] = None


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


class MessageOut(BaseModel):
    detail: str
