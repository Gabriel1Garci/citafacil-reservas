"""Configuración de la aplicación mediante variables de entorno.

Todas las opciones se pueden sobreescribir con variables de entorno o con un
archivo `.env` (ver `.env.example`). Así el mismo código corre en local (SQLite)
y en producción (PostgreSQL en Render) sin tocar nada.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Negocio / marca ---
    business_name: str = "Barbería Don Lucho"
    business_timezone: str = "America/Santiago"
    currency: str = "CLP"
    open_hour: int = 10          # apertura (hora local, 24h)
    close_hour: int = 20         # cierre (hora local, 24h)
    slot_interval_minutes: int = 30
    # Días cerrados: 0=lunes ... 6=domingo. Por defecto cierra domingo.
    closed_weekdays: str = "6"

    # --- Base de datos ---
    # En local: SQLite. En producción, define DATABASE_URL (PostgreSQL).
    database_url: str = "sqlite:///./citafacil.db"

    # --- Seguridad ---
    admin_token: str = "cambia-este-token-admin"
    cors_origins: str = "*"      # separado por comas, o "*" para todos

    # --- Twilio / WhatsApp ---
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""      # ej: "whatsapp:+14155238886"
    reminder_hours_before: int = 24     # cuántas horas antes recordar
    reminder_poll_minutes: int = 15     # cada cuánto revisa el programador

    # --- Helpers derivados ---
    @property
    def closed_weekdays_set(self) -> set[int]:
        return {int(x) for x in self.closed_weekdays.split(",") if x.strip() != ""}

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def twilio_enabled(self) -> bool:
        """True solo si están las 3 credenciales de Twilio."""
        return bool(
            self.twilio_account_sid
            and self.twilio_auth_token
            and self.twilio_whatsapp_from
        )


settings = Settings()
