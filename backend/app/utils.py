"""Utilidades: validación de teléfono chileno y manejo de fechas locales."""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import settings


class PhoneError(ValueError):
    """Error de validación de número telefónico."""


def normalize_cl_phone(raw: str) -> str:
    """Normaliza un celular chileno a formato E.164 (+569XXXXXXXX).

    Acepta entradas como:
        "+56 9 4291 6570", "56942916570", "9 4291 6570",
        "942916570", "+569 4291 6570"
    """
    digits = re.sub(r"[^\d]", "", raw or "")
    if digits.startswith("56"):          # prefijo país
        digits = digits[2:]
    if digits.startswith("0"):           # 0 de larga distancia
        digits = digits[1:]
    if len(digits) == 8:                 # faltó el 9 inicial del móvil
        digits = "9" + digits
    if len(digits) != 9 or not digits.startswith("9"):
        raise PhoneError(
            "Número de celular chileno inválido. Usa el formato +56 9 XXXX XXXX."
        )
    return "+56" + digits


def format_cl_phone(e164: str) -> str:
    """Formatea +56912345678 -> '+56 9 1234 5678' para mostrar."""
    d = e164.replace("+56", "")
    if len(d) == 9:
        return f"+56 {d[0]} {d[1:5]} {d[5:]}"
    return e164


def local_now() -> datetime:
    """Hora actual del negocio (naive, en la zona horaria configurada)."""
    return datetime.now(ZoneInfo(settings.business_timezone)).replace(tzinfo=None)


def to_local_naive(dt: datetime) -> datetime:
    """Convierte un datetime con zona a hora local naive; deja los naive igual."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(ZoneInfo(settings.business_timezone)).replace(tzinfo=None)
    return dt
