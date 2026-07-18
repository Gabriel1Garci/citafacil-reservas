"""Modelos de base de datos (SQLAlchemy)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base

# Estados posibles de una cita
STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_CANCELLED = "cancelled"
STATUS_DONE = "done"
VALID_STATUSES = {STATUS_PENDING, STATUS_CONFIRMED, STATUS_CANCELLED, STATUS_DONE}


class Service(Base):
    """Un servicio que ofrece el negocio (ej: Corte de pelo, 30 min, $8.000)."""

    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    duration_min = Column(Integer, nullable=False, default=30)
    price = Column(Integer, nullable=False, default=0)  # CLP, entero
    active = Column(Boolean, nullable=False, default=True)

    appointments = relationship("Appointment", back_populates="service")


class Appointment(Base):
    """Una reserva/cita hecha por un cliente."""

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(120), nullable=False)
    customer_phone = Column(String(20), nullable=False)   # E.164: +569XXXXXXXX
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    start_at = Column(DateTime, nullable=False, index=True)  # hora local (naive)
    end_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default=STATUS_PENDING)
    notes = Column(String(300), nullable=False, default="")
    reminder_sent = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    service = relationship("Service", back_populates="appointments")
