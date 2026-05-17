"""Configuración tipada vía pydantic-settings.

Carga env vars del entorno (en local: `.env` cargado por docker/uvicorn,
en prod: Secret Manager → env vars de Cloud Run).
Falla rápido al startup si falta config crítica.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings globales del backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_env: Literal["local", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ---- DB ----
    # En prod, `NEON_DATABASE_URL` (si existe) tiene prioridad sobre `DATABASE_URL`.
    database_url: str = Field(
        default="postgresql+asyncpg://megarepartos:megarepartos@localhost:5433/megarepartos",
    )
    neon_database_url: str | None = None

    # ---- Auth ----
    jwt_secret: str = "cambiame-en-local-y-en-secret-manager-en-prod"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_min: int = 60
    jwt_refresh_ttl_days: int = 14

    # ---- Google OAuth (se completa en TASK-001) ----
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_url: str = "http://localhost:8000/api/auth/google/callback"

    # ---- Google Maps (TASK-013) ----
    # Si está vacía, `infra/geocoding.py` devuelve None y no llama a Google.
    google_maps_api_key: str | None = None

    @property
    def effective_database_url(self) -> str:
        """URL efectiva: Neon en prod si está, default si no."""
        return self.neon_database_url or self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton cacheado. Usar como dependencia FastAPI."""
    return Settings()
