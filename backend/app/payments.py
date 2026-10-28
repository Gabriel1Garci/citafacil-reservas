"""Pasarela de pago SIMULADA (para desarrollo y demostración).

No se conecta a ningún proveedor real. Valida la tarjeta como lo haría un
formulario de pago (Luhn, vencimiento, CVV) y devuelve solo datos seguros:
marca y últimos 4 dígitos. El número completo y el CVV nunca se guardan ni se
registran en logs; viven únicamente durante esta validación.

Tarjetas de prueba: 4242 4242 4242 4242 (Visa, aprobada),
5555 5555 5555 4444 (Mastercard, aprobada), 4000 0000 0000 0002 (rechazada).
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

from .utils import local_now

DECLINED_LAST4 = "0002"  # tarjeta de prueba que siempre es rechazada


class PaymentError(ValueError):
    """Datos de pago inválidos."""


class PaymentDeclined(PaymentError):
    """La pasarela rechazó el cobro."""


@dataclass(frozen=True)
class CardInfo:
    """Datos NO sensibles de una tarjeta (lo único que se puede persistir)."""

    brand: str
    last4: str
    exp_month: int
    exp_year: int


@dataclass(frozen=True)
class ChargeResult:
    token: str
    amount: int


def luhn_ok(number: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def detect_brand(number: str) -> str:
    if number.startswith("4"):
        return "visa"
    if re.match(r"^(5[1-5]|2[2-7])", number):
        return "mastercard"
    if re.match(r"^3[47]", number):
        return "amex"
    return "unknown"


def _expired(exp_month: int, exp_year: int) -> bool:
    now = local_now()
    return (exp_year, exp_month) < (now.year, now.month)  # vale hasta fin del mes


def validate_card(number: str, exp_month: int, exp_year: int, cvv: str) -> CardInfo:
    digits = re.sub(r"[\s-]", "", number or "")
    if not digits.isdigit() or not 13 <= len(digits) <= 19 or not luhn_ok(digits):
        raise PaymentError("Número de tarjeta inválido.")
    if not 1 <= exp_month <= 12:
        raise PaymentError("Mes de vencimiento inválido.")
    if exp_year < 100:  # "29" -> 2029
        exp_year += 2000
    if _expired(exp_month, exp_year):
        raise PaymentError("La tarjeta está vencida.")
    brand = detect_brand(digits)
    expected_cvv = 4 if brand == "amex" else 3
    if not (cvv or "").isdigit() or len(cvv) != expected_cvv:
        raise PaymentError(f"El CVV debe tener {expected_cvv} dígitos.")
    return CardInfo(brand=brand, last4=digits[-4:], exp_month=exp_month, exp_year=exp_year)


def ensure_not_expired(info: CardInfo) -> None:
    """Para tarjetas guardadas: el vencimiento pudo pasar desde que se guardó."""
    if _expired(info.exp_month, info.exp_year):
        raise PaymentError("Tu tarjeta guardada está vencida. Ingresa una nueva.")


def charge(info: CardInfo, amount: int) -> ChargeResult:
    """Cobra `amount` (CLP, entero) a la tarjeta. Simulado: no hay red de por medio."""
    if amount <= 0:
        raise PaymentError("El monto a cobrar debe ser mayor que cero.")
    if info.last4 == DECLINED_LAST4:
        raise PaymentDeclined("Pago rechazado por el banco emisor.")
    return ChargeResult(token="tok_sim_" + secrets.token_hex(12), amount=amount)
