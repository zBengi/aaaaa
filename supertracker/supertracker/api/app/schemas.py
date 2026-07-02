"""Esquemas Pydantic de respuesta de la API REST."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SupermercadoOut(BaseModel):
    id: int
    nombre: str
    url_base: str
    activo: bool

    model_config = {"from_attributes": True}


class PrecioEnTienda(BaseModel):
    """Último precio de un producto en una tienda (para la comparativa)."""

    supermercado_id: int
    supermercado_nombre: str
    precio: float
    precio_oferta: float | None
    precio_efectivo: float          # min(precio, precio_oferta)
    url_producto: str
    registrado_en: datetime


class ProductoResumen(BaseModel):
    """Producto con resumen de precios actuales (para el listado/búsqueda)."""

    id: int
    nombre: str
    categoria: str
    precio_min: float | None
    precio_max: float | None
    supermercado_mas_barato: str | None
    n_tiendas: int
    ahorro: float | None            # precio_max - precio_min
    ultima_actualizacion: datetime | None


class ProductoDetalle(BaseModel):
    id: int
    nombre: str
    categoria: str
    descripcion: str | None
    creado_en: datetime

    model_config = {"from_attributes": True}


class ComparativaOut(BaseModel):
    producto: ProductoDetalle
    precios: list[PrecioEnTienda]
    mejor_precio: PrecioEnTienda | None


class HistorialPunto(BaseModel):
    supermercado_nombre: str
    precio: float
    precio_oferta: float | None
    registrado_en: datetime


class HistorialOut(BaseModel):
    producto_id: int
    producto_nombre: str
    dias: int
    puntos: list[HistorialPunto]


class StatsOut(BaseModel):
    total_productos: int
    total_supermercados: int
    total_registros_precio: int
    ultima_actualizacion: datetime | None


class PaginatedProductos(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ProductoResumen]
