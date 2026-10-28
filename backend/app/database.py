"""Conexión a la base de datos con SQLAlchemy.

Funciona con SQLite (local) y PostgreSQL (producción) según DATABASE_URL.
"""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

logger = logging.getLogger("citafacil.db")


def _normalize_url(url: str) -> str:
    # Render/Heroku entregan "postgres://", SQLAlchemy espera "postgresql://".
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = _normalize_url(settings.database_url)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: entrega una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema(bind=None) -> None:
    """Crea las tablas y agrega columnas nuevas a tablas ya existentes.

    `create_all` no modifica tablas que ya existen, así que una base creada antes de
    una nueva versión no tendría las columnas nuevas. Solo se agregan columnas
    anulables (no destructivo); no reemplaza a una herramienta de migraciones real.
    """
    bind = bind or engine
    Base.metadata.create_all(bind=bind)
    existing_tables = set(inspect(bind).get_table_names())
    with bind.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            have = {c["name"] for c in inspect(conn).get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                if not col.nullable:
                    logger.warning("Columna %s.%s no anulable: requiere migración manual.", table.name, col.name)
                    continue
                ddl = col.type.compile(dialect=bind.dialect)
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl}"))
                if col.unique or col.index:
                    unique = "UNIQUE " if col.unique else ""
                    conn.execute(text(
                        f"CREATE {unique}INDEX IF NOT EXISTS ix_{table.name}_{col.name} ON {table.name} ({col.name})"
                    ))
