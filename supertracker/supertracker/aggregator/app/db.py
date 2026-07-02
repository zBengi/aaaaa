"""Conexión a PostgreSQL para el agregador.

Crea el engine y la fábrica de sesiones de SQLAlchemy, y ofrece una utilidad
para esperar a que la base de datos esté lista antes de comenzar a consumir.
"""
from __future__ import annotations

import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from . import config

logger = logging.getLogger("aggregator.db")

engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,   # detecta conexiones muertas antes de usarlas
    pool_size=5,
    max_overflow=10,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def wait_for_db(max_retries: int = 30, retry_delay: float = 2.0) -> None:
    """Bloquea hasta que PostgreSQL acepte conexiones (o agote los reintentos)."""
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Conexión a PostgreSQL establecida")
            return
        except OperationalError:
            logger.warning("PostgreSQL no disponible (intento %s/%s); reintentando…", attempt, max_retries)
            time.sleep(retry_delay)
    raise RuntimeError("No fue posible conectar a PostgreSQL")
