"""Perfil del cliente recurrente: ver y olvidar los datos guardados (US1).

Se autentica con la cabecera X-Customer-Token (secreto que guarda el navegador).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/customers", tags=["Clientes"])


def current_customer(
    db: Session = Depends(get_db),
    x_customer_token: Optional[str] = Header(None, alias="X-Customer-Token"),
) -> models.Customer:
    customer = crud.get_customer_by_token(db, x_customer_token)
    if not customer:
        raise HTTPException(status_code=401, detail="Token de cliente inválido.")
    return customer


@router.get("/me", response_model=schemas.CustomerOut, summary="Mis datos guardados")
def my_profile(customer: models.Customer = Depends(current_customer)):
    return customer


@router.delete("/me", response_model=schemas.MessageOut, summary="Olvidar mis datos guardados")
def forget_me(customer: models.Customer = Depends(current_customer), db: Session = Depends(get_db)):
    crud.delete_customer(db, customer)
    return {"detail": "Tus datos guardados fueron eliminados."}
