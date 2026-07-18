"""Endpoints de administración (requieren cabecera X-Admin-Token)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth import require_admin
from ..database import get_db
from ..reminders import run_reminders

router = APIRouter(
    prefix="/api/admin",
    tags=["Administración"],
    dependencies=[Depends(require_admin)],
)


# ---------- Servicios ----------
@router.get("/services", response_model=list[schemas.ServiceOut], summary="Listar todos los servicios")
def all_services(db: Session = Depends(get_db)):
    return crud.list_services(db, only_active=False)


@router.post("/services", response_model=schemas.ServiceOut, status_code=201, summary="Crear servicio")
def add_service(payload: schemas.ServiceCreate, db: Session = Depends(get_db)):
    return crud.create_service(db, payload)


@router.put("/services/{service_id}", response_model=schemas.ServiceOut, summary="Editar servicio")
def edit_service(service_id: int, payload: schemas.ServiceUpdate, db: Session = Depends(get_db)):
    service = crud.get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    return crud.update_service(db, service, payload)


@router.delete("/services/{service_id}", response_model=schemas.MessageOut, summary="Eliminar servicio")
def remove_service(service_id: int, db: Session = Depends(get_db)):
    service = crud.get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    crud.delete_service(db, service)
    return {"detail": "Servicio eliminado."}


# ---------- Citas ----------
@router.get("/appointments", response_model=list[schemas.AppointmentOut], summary="Listar citas")
def all_appointments(
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    day: Optional[date] = Query(None, alias="date", description="Filtrar por fecha YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    return crud.list_appointments(db, status=status, day=day)


@router.patch("/appointments/{appt_id}", response_model=schemas.AppointmentOut, summary="Cambiar estado")
def change_status(appt_id: int, payload: schemas.AppointmentStatusUpdate, db: Session = Depends(get_db)):
    appt = crud.get_appointment(db, appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada.")
    return crud.set_status(db, appt, payload.status)


@router.delete("/appointments/{appt_id}", response_model=schemas.MessageOut, summary="Eliminar cita")
def remove_appointment(appt_id: int, db: Session = Depends(get_db)):
    appt = crud.get_appointment(db, appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada.")
    crud.delete_appointment(db, appt)
    return {"detail": "Cita eliminada."}


# ---------- Estadísticas y recordatorios ----------
@router.get("/stats", response_model=schemas.StatsOut, summary="Estadísticas")
def get_stats(db: Session = Depends(get_db)):
    return crud.stats(db)


@router.post("/reminders/run", summary="Enviar recordatorios ahora")
def trigger_reminders(db: Session = Depends(get_db)):
    return run_reminders(db)
