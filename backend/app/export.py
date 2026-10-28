"""Exportación de reservas a CSV (US5)."""
from __future__ import annotations

import csv
import io

from . import models

HEADER = [
    "ID", "Fecha", "Hora", "Cliente", "Teléfono", "Servicio", "Precio",
    "Estado", "Pago", "Tarjeta (últimos 4)", "Notas", "Creada",
]

# Excel/Sheets interpretan como fórmula una celda que empieza con estos caracteres.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value) -> str:
    """Neutraliza la inyección de fórmulas CSV anteponiendo una comilla simple."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def appointments_to_csv(appointments: list[models.Appointment]) -> bytes:
    """CSV en UTF-8 con BOM (para que Excel muestre bien los acentos)."""
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerow(HEADER)
    for a in appointments:
        svc = a.service
        writer.writerow([
            a.id,
            a.start_at.strftime("%Y-%m-%d"),
            a.start_at.strftime("%H:%M"),
            safe_cell(a.customer_name),
            a.customer_phone,  # ya validado como E.164 (+56...) por el esquema
            safe_cell(svc.name if svc else ""),
            svc.price if svc else "",
            a.status,
            a.payment_status or "unpaid",
            a.payment_last4 or "",
            safe_cell(a.notes),
            a.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    return buf.getvalue().encode("utf-8-sig")
