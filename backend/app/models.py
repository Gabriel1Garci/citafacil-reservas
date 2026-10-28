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

# Estado de pago de una cita
PAYMENT_UNPAID = "unpaid"
PAYMENT_PAID = "paid"
PAYMENT_FREE = "free"


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
    # Código que el cliente usa para cancelar (nullable: citas anteriores a US4)
    cancel_code = Column(String(12), unique=True, index=True, nullable=True)
    # Pago (US1). Nunca se guarda el número completo ni el CVV.
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    payment_status = Column(String(12), nullable=True, default=PAYMENT_UNPAID)
    paid_amount = Column(Integer, nullable=True)
    payment_last4 = Column(String(4), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    service = relationship("Service", back_populates="appointments")


class Customer(Base):
    """Perfil de cliente recurrente.

    Se identifica por un token secreto que vive en el navegador del cliente
    (solo se guarda su hash). El teléfono NO sirve para consultar el perfil:
    así nadie puede ver datos de otra persona conociendo su número.
    """

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    payment = relationship(
        "PaymentMethod", back_populates="customer", uselist=False, cascade="all, delete-orphan"
    )


class PaymentMethod(Base):
    """Tarjeta guardada: solo datos no sensibles (marca, últimos 4, vencimiento)."""

    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, unique=True)
    holder = Column(String(80), nullable=False)
    brand = Column(String(12), nullable=False)
    last4 = Column(String(4), nullable=False)
    exp_month = Column(Integer, nullable=False)
    exp_year = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="payment")
