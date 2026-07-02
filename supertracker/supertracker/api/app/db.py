"""Conexión a PostgreSQL para la API REST."""
from __future__ import annotations

import logging
import time
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from . import config

logger = logging.getLogger("api.db")

engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: una sesión por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(max_retries: int = 30, retry_delay: float = 2.0) -> None:
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
