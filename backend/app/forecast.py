"""Previsión de demanda a partir del histórico de reservas (US3).

Modelo deliberadamente simple y explicable (no es una caja negra):

1. **Estacionalidad semanal**: para cada día de la semana se calcula el promedio de
   reservas de las últimas `history_weeks` semanas (solo días en que el negocio abre).
2. **Tendencia**: razón entre las reservas de las últimas 4 semanas y las 4 anteriores,
   acotada a [0.7, 1.3] para que un par de semanas atípicas no dispare la previsión.
3. **Previsión** de un día futuro = promedio del día de la semana x tendencia, con piso
   en las reservas que ya existen para esa fecha.
4. **Utilización** = previsión / capacidad diaria (horarios de inicio por día). Según el
   nivel se sugiere un ajuste de precio: alta (>= 70 %) +10 %, baja (< 35 %) -10 %.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from . import models

WEEKDAYS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
WEEKDAYS_FULL_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

HIGH_UTILIZATION = 0.70
LOW_UTILIZATION = 0.35
PRICE_STEP_PCT = 10
TREND_MIN, TREND_MAX = 0.7, 1.3


def daily_counts(db: Session, start: date, end: date) -> dict[date, int]:
    """Reservas no canceladas por día en [start, end] (ambos inclusive)."""
    rows = (
        db.query(models.Appointment.start_at)
        .filter(
            models.Appointment.status != models.STATUS_CANCELLED,
            models.Appointment.start_at >= datetime.combine(start, time.min),
            models.Appointment.start_at <= datetime.combine(end, time.max),
        )
        .all()
    )
    return dict(Counter(r[0].date() for r in rows))


def _level(utilization: float) -> str:
    if utilization >= HIGH_UTILIZATION:
        return "high"
    if utilization < LOW_UTILIZATION:
        return "low"
    return "normal"


def _price_change(level: str) -> int:
    return {"high": PRICE_STEP_PCT, "low": -PRICE_STEP_PCT}.get(level, 0)


def build_forecast(
    counts: dict[date, int],
    today: date,
    horizon_days: int,
    history_weeks: int,
    capacity: int,
    closed_weekdays: set[int],
) -> dict:
    """Calcula histórico, promedios por día de la semana y previsión (función pura)."""
    capacity = max(capacity, 1)
    history_start = today - timedelta(weeks=history_weeks)

    # --- promedio por día de la semana (solo días abiertos, antes de hoy) ---
    per_weekday: dict[int, list[int]] = {wd: [] for wd in range(7)}
    d = history_start
    while d < today:
        if d.weekday() not in closed_weekdays:
            per_weekday[d.weekday()].append(counts.get(d, 0))
        d += timedelta(days=1)
    avg = {wd: (sum(v) / len(v) if v else 0.0) for wd, v in per_weekday.items()}

    # --- tendencia: últimas 4 semanas vs 4 anteriores ---
    def window_total(start: date, end: date) -> int:
        total, day = 0, start
        while day < end:
            if day.weekday() not in closed_weekdays:
                total += counts.get(day, 0)
            day += timedelta(days=1)
        return total

    recent = window_total(today - timedelta(weeks=4), today)
    previous = window_total(today - timedelta(weeks=8), today - timedelta(weeks=4))
    trend = recent / previous if previous > 0 else 1.0
    trend = min(max(trend, TREND_MIN), TREND_MAX)

    # --- histórico semanal (semanas lunes-domingo; la actual es parcial) ---
    current_monday = today - timedelta(days=today.weekday())
    history_weekly = []
    for k in range(history_weeks):
        week_start = current_monday - timedelta(weeks=history_weeks - 1 - k)
        count = sum(counts.get(week_start + timedelta(days=i), 0)
                    for i in range(7) if week_start + timedelta(days=i) < today)
        history_weekly.append({
            "week_start": week_start.isoformat(),
            "count": count,
            "partial": week_start == current_monday,
        })

    by_weekday = [
        {"weekday": wd, "label": WEEKDAYS_ES[wd], "avg": round(avg[wd], 2), "closed": wd in closed_weekdays}
        for wd in range(7)
    ]

    # --- previsión ---
    forecast = []
    for i in range(1, horizon_days + 1):
        day = today + timedelta(days=i)
        wd = day.weekday()
        booked = counts.get(day, 0)
        if wd in closed_weekdays:
            expected, utilization, level, price = 0.0, 0.0, "closed", 0
        else:
            # No se pueden atender más reservas que horarios: se acota a la capacidad.
            expected = round(min(max(avg[wd] * trend, float(booked)), float(capacity)), 1)
            utilization = min(expected / capacity, 1.0)
            level = _level(utilization)
            price = _price_change(level)
        forecast.append({
            "date": day.isoformat(),
            "weekday": WEEKDAYS_ES[wd],
            "expected": expected,
            "booked": booked,
            "capacity": capacity,
            "utilization": round(utilization, 3),
            "level": level,
            "price_change_pct": price,
        })

    return {
        "history_weeks": history_weeks,
        "capacity_per_day": capacity,
        "trend_factor": round(trend, 3),
        "history_weekly": history_weekly,
        "by_weekday": by_weekday,
        "forecast": forecast,
        "recommendations": _recommendations(forecast, trend),
    }


def _fmt(day_iso: str) -> str:
    d = date.fromisoformat(day_iso)
    return f"{WEEKDAYS_FULL_ES[d.weekday()]} {d.day:02d}-{d.month:02d}"


def _recommendations(forecast: list[dict], trend: float) -> list[str]:
    open_days = [f for f in forecast if f["level"] != "closed"]
    out: list[str] = []
    if not open_days:
        return ["No hay días de atención en el período de previsión."]

    if trend >= 1.05:
        out.append(f"La demanda de las últimas 4 semanas subió un {round((trend - 1) * 100)} % "
                   "respecto de las 4 anteriores.")
    elif trend <= 0.95:
        out.append(f"La demanda de las últimas 4 semanas bajó un {round((1 - trend) * 100)} % "
                   "respecto de las 4 anteriores.")

    peak = max(open_days, key=lambda f: f["expected"])
    if peak["level"] == "high":
        out.append(f"Mayor demanda prevista: {_fmt(peak['date'])} ({peak['expected']} de {peak['capacity']} "
                   f"horarios, {round(peak['utilization'] * 100)} %). Sugerencia: subir precios un "
                   f"{PRICE_STEP_PCT} % y reforzar el personal ese día.")
    else:
        out.append(f"Ningún día supera el {round(HIGH_UTILIZATION * 100)} % de ocupación prevista; "
                   "no hace falta subir precios ni reforzar personal.")

    lows = [f for f in open_days if f["level"] == "low"]
    if lows:
        names = ", ".join(_fmt(f["date"]) for f in lows[:4]) + ("…" if len(lows) > 4 else "")
        out.append(f"Baja demanda prevista ({len(lows)} días: {names}). Sugerencia: promoción del "
                   f"{PRICE_STEP_PCT} % o reducir horas de personal esos días.")
    return out
