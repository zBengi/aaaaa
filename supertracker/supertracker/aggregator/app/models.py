"""Modelos SQLAlchemy que mapean el esquema de la base de datos.

Reflejan exactamente las tablas definidas en db/init/01_schema.sql. El
agregador no crea el esquema (lo hace el init de PostgreSQL); estos modelos
sólo sirven para insertar/consultar de forma segura mediante el ORM.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
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

    precios: Mapped[list["Precio"]] = relationship(back_populates="supermercado")


class Producto(Base):
    __tablename__ = "producto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped["TIMESTAMP"] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.now()
    )

    precios: Mapped[list["Precio"]] = relationship(back_populates="producto")


class Precio(Base):
    __tablename__ = "precio"
    __table_args__ = (
        CheckConstraint("precio >= 0", name="ck_precio_no_negativo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("producto.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supermercado_id: Mapped[int] = mapped_column(
        ForeignKey("supermercado.id", ondelete="CASCADE"), nullable=False, index=True
    )
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    precio_oferta: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    url_producto: Mapped[str] = mapped_column(String(500), nullable=False)
    registrado_en: Mapped["TIMESTAMP"] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.now(), index=True
    )

    producto: Mapped["Producto"] = relationship(back_populates="precios")
    supermercado: Mapped["Supermercado"] = relationship(back_populates="precios")
