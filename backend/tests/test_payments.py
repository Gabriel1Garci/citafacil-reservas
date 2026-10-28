"""US1: pasarela de pago simulada (validación de tarjeta, sin guardar datos sensibles)."""
import pytest

from app.payments import (
    CardInfo,
    PaymentDeclined,
    PaymentError,
    charge,
    detect_brand,
    luhn_ok,
    validate_card,
)

VISA = "4242 4242 4242 4242"
MASTERCARD = "5555 5555 5555 4444"
AMEX = "3782 822463 10005"
DECLINED = "4000 0000 0000 0002"


def test_luhn():
    assert luhn_ok("4242424242424242")
    assert luhn_ok("378282246310005")
    assert not luhn_ok("4242424242424241")


def test_brand_detection():
    assert detect_brand("4242424242424242") == "visa"
    assert detect_brand("5555555555554444") == "mastercard"
    assert detect_brand("378282246310005") == "amex"
    assert detect_brand("6011000000000004") == "unknown"


def test_validate_card_ok_returns_only_safe_data():
    info = validate_card(VISA, 12, 2099, "123")
    assert isinstance(info, CardInfo)
    assert (info.brand, info.last4, info.exp_month, info.exp_year) == ("visa", "4242", 12, 2099)
    assert not hasattr(info, "number") and not hasattr(info, "cvv")


def test_validate_card_accepts_two_digit_year():
    assert validate_card(MASTERCARD, 1, 99, "123").exp_year == 2099


def test_validate_card_rejects_bad_number():
    with pytest.raises(PaymentError):
        validate_card("4242 4242 4242 4241", 12, 2099, "123")


def test_validate_card_rejects_expired():
    with pytest.raises(PaymentError, match="vencid"):
        validate_card(VISA, 1, 2020, "123")


def test_validate_card_cvv_rules():
    with pytest.raises(PaymentError):
        validate_card(VISA, 12, 2099, "12")
    with pytest.raises(PaymentError):
        validate_card(AMEX, 12, 2099, "123")  # Amex exige 4 dígitos
    assert validate_card(AMEX, 12, 2099, "1234").brand == "amex"


def test_charge_approved_returns_token_without_card_number():
    info = validate_card(VISA, 12, 2099, "123")
    result = charge(info, 8000)
    assert result.token.startswith("tok_sim_")
    assert "4242424242424242" not in result.token


def test_charge_declined_test_card():
    info = validate_card(DECLINED, 12, 2099, "123")
    with pytest.raises(PaymentDeclined):
        charge(info, 8000)


def test_charge_rejects_non_positive_amount():
    info = validate_card(VISA, 12, 2099, "123")
    with pytest.raises(PaymentError):
        charge(info, 0)
