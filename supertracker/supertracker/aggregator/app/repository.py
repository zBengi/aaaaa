"""Lógica de persistencia del agregador.

Por cada mensaje válido:
  1. Resuelve (o crea) el supermercado por su nombre.
  2. Resuelve (o crea) el producto por su nombre.
  3. Inserta una nueva fila de precio (append-only → historial).

El "get or create" usa INSERT ... ON CONFLICT DO NOTHING + SELECT, patrón
idempotente y seguro ante múltiples instancias del agregador consumiendo en
paralelo (competing consumers).
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .models import Precio, Producto, Supermercado
from .schemas import IncomingPrice

logger = logging.getLogger("aggregator.repository")


def _base_url_from_product(url_producto: str) -> str:
    """Deriva la URL base (esquema + host) a partir de la URL del producto."""
    parsed = urlparse(url_producto)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return url_producto[:200]


def _get_or_create_supermercado(session: Session, nombre: str, fallback_url: str) -> Supermercado:
    existing = session.execute(
        select(Supermercado).where(Supermercado.nombre == nombre)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    session.execute(
        pg_insert(Supermercado)
        .values(nombre=nombre, url_base=fallback_url, activo=True)
        .on_conflict_do_nothing(index_elements=["nombre"])
    )
    session.flush()
    return session.execute(
        select(Supermercado).where(Supermercado.nombre == nombre)
    ).scalar_one()


def _get_or_create_producto(session: Session, nombre: str, categoria: str) -> Producto:
    existing = session.execute(
        select(Producto).where(Producto.nombre == nombre)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    session.execute(
        pg_insert(Producto)
        .values(nombre=nombre, categoria=categoria)
        .on_conflict_do_nothing(index_elements=["nombre"])
    )
    session.flush()
    return session.execute(
        select(Producto).where(Producto.nombre == nombre)
    ).scalar_one()


def persist_price(session: Session, msg: IncomingPrice) -> None:
    """Persiste un mensaje de precio dentro de una transacción."""
    supermercado = _get_or_create_supermercado(
        session, msg.supermercado, _base_url_from_product(msg.url_producto)
    )
    producto = _get_or_create_producto(session, msg.nombre_producto, msg.categoria)

    session.add(
        Precio(
            producto_id=producto.id,
            supermercado_id=supermercado.id,
            precio=msg.precio,
            precio_oferta=msg.precio_oferta,
            url_producto=msg.url_producto,
            registrado_en=msg.registrado_en,
        )
    )
    session.commit()
