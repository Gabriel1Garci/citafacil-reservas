"""Autenticación simple para la administración (token por cabecera HTTP)."""
from __future__ import annotations

from fastapi import Header, HTTPException, status

from .config import settings


def require_admin(x_admin_token: str = Header(..., alias="X-Admin-Token")) -> None:
    """Valida la cabecera X-Admin-Token contra el token configurado."""
    if x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de administrador inválido.",
        )
