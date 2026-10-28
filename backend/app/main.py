"""Punto de entrada de la API CitaFácil (FastAPI)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from . import __version__
from .config import settings
from .database import ensure_schema
from .reminders import run_reminders_job
from .routers import admin, customers, public, scores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("citafacil")

scheduler: BackgroundScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    ensure_schema()

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
        "citas y recordatorios por WhatsApp. Incluye el ranking mundial del "
        "juego ÚLTIMA RONDA 3D. Hecho por Giancarlos Alfaro."
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
    expose_headers=["Content-Disposition"],  # para leer el nombre del CSV exportado
)

app.include_router(public.router)
app.include_router(customers.router)
app.include_router(admin.router)
app.include_router(scores.router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc: RequestValidationError):
    """Respuesta 422 SIN el valor recibido (`input`/`ctx`).

    Por defecto FastAPI reenvía lo que envió el cliente; en errores de todo el modelo
    eso incluiría el número de tarjeta y el CVV en claro.
    """
    safe = [{k: v for k, v in err.items() if k not in ("input", "ctx", "url")} for err in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": safe})


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


# Acepta GET y HEAD: los monitores de uptime (UptimeRobot, etc.) usan HEAD por
# defecto; sin HEAD respondería 405 y el monitor marcaría el servicio como caído.
@app.api_route("/health", methods=["GET", "HEAD"], tags=["Sistema"], summary="Estado del servicio")
def health():
    return {"status": "ok", "twilio": settings.twilio_enabled}
