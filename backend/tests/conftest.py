"""Configuración común de pytest: BD aislada y datos mínimos por test."""
import os
import tempfile

# Usar una base de datos de prueba aislada ANTES de importar la app.
# (Directorio temporal del sistema: funciona en Windows, Linux y macOS.)
_TEST_DB = os.path.join(tempfile.gettempdir(), "citafacil_test.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.replace("\\", "/")
os.environ["ADMIN_TOKEN"] = "test-token"

import pytest  # noqa: E402

from app import models  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add(models.Service(name="Corte", duration_min=30, price=8000, active=True))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
