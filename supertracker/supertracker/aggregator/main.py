"""Entrypoint del Servicio Agregador.

Arranca un pequeño servidor FastAPI (salud y métricas) en un hilo en segundo
plano y ejecuta el consumidor de RabbitMQ en el hilo principal. Así el
contenedor expone un healthcheck y, a la vez, procesa la cola de precios.
"""
from __future__ import annotations

import logging
import threading

import uvicorn
from fastapi import FastAPI

from app import config
from app.consumer import STATS, run_consumer
from app.db import wait_for_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aggregator.main")

app = FastAPI(title="SuperTracker — Servicio Agregador", version="2.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "aggregator"}


@app.get("/metrics")
def metrics() -> dict:
    """Contadores básicos de procesamiento para observabilidad."""
    import time
    return {
        "mensajes_procesados": STATS["processed"],
        "mensajes_fallidos": STATS["failed"],
        "ultimo_error": STATS["last_error"],
        "uptime_segundos": round(time.time() - STATS["started_at"], 1),
    }


def _start_health_server() -> None:
    uvicorn.run(app, host=config.HEALTH_HOST, port=config.HEALTH_PORT, log_level="warning")


def main() -> None:
    wait_for_db()

    # Servidor de salud en un hilo daemon.
    threading.Thread(target=_start_health_server, daemon=True).start()
    logger.info("Servidor de salud en %s:%s", config.HEALTH_HOST, config.HEALTH_PORT)

    # Consumidor en el hilo principal (bloqueante).
    run_consumer()


if __name__ == "__main__":
    main()
