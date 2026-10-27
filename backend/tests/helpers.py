"""Utilidades compartidas por los tests."""
from datetime import timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.utils import local_now

client = TestClient(app)
ADMIN = {"X-Admin-Token": "test-token"}


def next_open_day_at(hour: int, minute: int = 0, days: int = 1):
    """Próximo día abierto (no domingo), `days` días adelante, a la hora dada."""
    d = (local_now() + timedelta(days=days)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    while d.weekday() == 6:  # saltar domingo
        d += timedelta(days=1)
    return d
