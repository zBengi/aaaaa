"""Validación de los mensajes entrantes en el agregador.

Replica el contrato Pub/Sub del scraper. Cada servicio valida su propio
contrato de forma independiente (servicios desacoplados): si llega un mensaje
malformado, Pydantic lanza ValidationError y el consumidor lo descarta sin
romper el flujo.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class IncomingPrice(BaseModel):
    scraper_id: str
    supermercado: str = Field(..., min_length=1)
    nombre_producto: str = Field(..., min_length=1)
    categoria: str = Field(default="general")
    precio: float = Field(..., ge=0)
    precio_oferta: float | None = Field(default=None, ge=0)
    url_producto: str = Field(..., min_length=1)
    timestamp: str

    @field_validator("timestamp")
    @classmethod
    def _validate_ts(cls, value: str) -> str:
        datetime.fromisoformat(value)
        return value

    @property
    def registrado_en(self) -> datetime:
        return datetime.fromisoformat(self.timestamp)
