"""Aplicación FastAPI de la API REST de SuperTracker.

Expone los endpoints que consume el frontend React. Todas las rutas cuelgan
del prefijo /api para integrarse limpiamente con el reverse proxy Traefik.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.db import wait_for_db
from app.routers import catalogo, productos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("api.main")

app = FastAPI(
    title="SuperTracker — API REST",
    description="API de comparación de precios de supermercados de Chile",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    wait_for_db()
    logger.info("API REST lista")


@app.get("/api/health", tags=["salud"])
def health() -> dict:
    return {"status": "ok", "service": "api"}


# Routers bajo /api
app.include_router(catalogo.router, prefix="/api")
app.include_router(productos.router, prefix="/api")
