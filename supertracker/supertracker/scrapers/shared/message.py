"""Contrato de mensajes Pub/Sub.

Define el esquema JSON que viaja por RabbitMQ desde los scrapers hacia el
servicio agregador. Corresponde a la "Tabla de mensajes (RabbitMQ — formato
JSON)" del diccionario de datos.

Mejora de la Iteración 2: se incorpora el campo opcional ``categoria`` para
poder poblar ``producto.categoria`` (NOT NULL) con un valor significativo.
Es retrocompatible: si un mensaje no la trae, el agregador usa "general".
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class PriceMessage(BaseModel):
    """Mensaje publicado por un scraper con el precio de un producto."""

    scraper_id: str = Field(..., description="Identificador del scraper que originó el mensaje")
    supermercado: str = Field(..., description="Nombre del supermercado (Jumbo / Líder / Unimarc)")
    nombre_producto: str = Field(..., min_length=1, description="Nombre del producto scrapeado")
    categoria: str = Field(default="general", description="Categoría del producto (mejora It.2)")
    precio: float = Field(..., ge=0, description="Precio normal extraído del sitio")
    precio_oferta: float | None = Field(default=None, ge=0, description="Precio de oferta si existe")
    url_producto: str = Field(..., description="URL directa al producto")
    timestamp: str = Field(..., description="ISO 8601 timestamp del momento del scraping")

    @field_validator("timestamp")
    @classmethod
    def _validate_iso8601(cls, value: str) -> str:
        # Lanza ValueError si el formato no es ISO 8601 válido.
        datetime.fromisoformat(value)
        return value

    @staticmethod
    def now_iso() -> str:
        """Devuelve el instante actual en ISO 8601 con zona horaria."""
        return datetime.now(timezone.utc).isoformat()
