"""Ranking mundial del juego ÚLTIMA RONDA 3D.

Reutiliza la infraestructura de CitaFácil (misma aplicación FastAPI y misma
base de datos) para guardar y consultar los mejores puntajes del juego.

Endpoints:
    POST /api/scores       -> registra un puntaje
    GET  /api/scores/top   -> devuelve los mejores puntajes
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Integer, String, desc
from sqlalchemy.orm import Session

from ..database import Base, get_db


class Score(Base):
    """Puntaje de una partida del juego."""

    __tablename__ = "game_scores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), nullable=False)
    round = Column(Integer, nullable=False, default=0)
    score = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ScoreIn(BaseModel):
    """Datos que envía el juego al terminar una partida."""

    name: str = Field("Anónimo", max_length=20)
    round: int = Field(0, ge=0, le=100_000)
    score: int = Field(0, ge=0, le=100_000_000)


router = APIRouter(prefix="/api/scores", tags=["Ranking"])


@router.post("", summary="Enviar un puntaje", status_code=201)
def create_score(payload: ScoreIn, db: Session = Depends(get_db)):
    """Guarda el puntaje de una partida y lo devuelve."""
    name = (payload.name or "").strip()[:20] or "Anónimo"
    row = Score(name=name, round=payload.round, score=payload.score)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"name": row.name, "round": row.round, "score": row.score}


@router.get("/top", summary="Mejores puntajes del mundo")
def top_scores(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """Devuelve los mejores puntajes ordenados de mayor a menor."""
    rows = (
        db.query(Score)
        .order_by(desc(Score.score), desc(Score.round))
        .limit(limit)
        .all()
    )
    return [{"name": r.name, "round": r.round, "score": r.score} for r in rows]
