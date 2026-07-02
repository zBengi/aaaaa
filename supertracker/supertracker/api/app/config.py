"""Configuración de la API REST (lectura desde variables de entorno)."""
from __future__ import annotations

import os

# --- Base de datos --------------------------------------------------------
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "supertracker")
POSTGRES_USER = os.getenv("POSTGRES_USER", "supertracker")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "supertracker")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

# --- CORS -----------------------------------------------------------------
# Orígenes permitidos para el frontend. En despliegue se restringe al dominio
# real; en local se admite cualquiera ("*") para simplificar el demo.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# --- Servidor -------------------------------------------------------------
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Tamaño de página por defecto y máximo para los listados.
DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))
