"""Punto de entrada de la API CitaFácil (FastAPI)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import __version__
from .config import settings
from .database import Base, engine
from .reminders import run_reminders_job
from .routers import admin, public

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("citafacil")

scheduler: BackgroundScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    Base.metadata.create_all(bind=engine)

    global scheduler
    scheduler = BackgroundScheduler(timezone=settings.business_timezone)
    scheduler.add_job(
        run_reminders_job,
        trigger="interval",
        minutes=settings.reminder_poll_minutes,
        id="reminders",
    )
    scheduler.start()
    logger.info(
        "CitaFácil %s iniciado. WhatsApp: %s.",
        __version__,
        "Twilio ACTIVO" if settings.twilio_enabled else "modo demo",
    )
    yield
    # --- shutdown ---
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="CitaFácil API",
    description=(
        "API de reservas para pequeños negocios: servicios, disponibilidad, "
        "citas y recordatorios por WhatsApp. Hecho por Giancarlos Alfaro."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,  # usamos token por cabecera, no cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)
app.include_router(admin.router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


# Acepta GET y HEAD: los monitores de uptime (UptimeRobot, etc.) usan HEAD por
# defecto; sin HEAD respondería 405 y el monitor marcaría el servicio como caído.
@app.api_route("/health", methods=["GET", "HEAD"], tags=["Sistema"], summary="Estado del servicio")
def health():
    return {"status": "ok", "twilio": settings.twilio_enabled}
