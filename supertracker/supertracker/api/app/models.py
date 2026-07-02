"""Modelos SQLAlchemy de la API (espejo del esquema de la base de datos).

Cada servicio independiente declara sus propios modelos; esto evita acoplar la
API y el agregador a una librería compartida y respeta la autonomía de los
servicios del diseño distribuido.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TIMESTAMP


class Base(DeclarativeBase):
    pass


class Supermercado(Base):
    __tablename__ = "supermercado"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    url_base: Mapped[str] = mapped_column(String(200), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Producto(Base):
    __tablename__ = "producto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped["TIMESTAMP"] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class Precio(Base):
    __tablename__ = "precio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id", ondelete="CASCADE"), nullable=False)
    supermercado_id: Mapped[int] = mapped_column(ForeignKey("supermercado.id", ondelete="CASCADE"), nullable=False)
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    precio_oferta: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    url_producto: Mapped[str] = mapped_column(String(500), nullable=False)
    registrado_en: Mapped["TIMESTAMP"] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())

    producto: Mapped["Producto"] = relationship()
    supermercado: Mapped["Supermercado"] = relationship()
