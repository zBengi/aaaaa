"""Endpoints de productos: búsqueda, detalle, comparativa e historial."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import config, crud, schemas
from ..db import get_db

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("", response_model=schemas.PaginatedProductos)
def buscar_productos(
    q: str | None = Query(None, description="Texto a buscar en el nombre del producto"),
    categoria: str | None = Query(None, description="Filtra por categoría exacta"),
    page: int = Query(1, ge=1, description="Número de página (1-indexado)"),
    page_size: int = Query(config.DEFAULT_PAGE_SIZE, ge=1, le=config.MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    """Busca productos y devuelve un resumen de precios actuales por producto.

    Cada item incluye el precio mínimo y máximo vigente entre tiendas, el
    supermercado más barato y el ahorro potencial.
    """
    return crud.search_productos(db, q=q, categoria=categoria, page=page, page_size=page_size)


@router.get("/{producto_id}", response_model=schemas.ProductoDetalle)
def detalle_producto(producto_id: int, db: Session = Depends(get_db)):
    """Devuelve los datos básicos de un producto."""
    producto = crud.get_producto(db, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.get("/{producto_id}/comparativa", response_model=schemas.ComparativaOut)
def comparativa_producto(producto_id: int, db: Session = Depends(get_db)):
    """Compara el último precio del producto en cada supermercado activo."""
    comparativa = crud.get_comparativa(db, producto_id)
    if comparativa is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return comparativa


@router.get("/{producto_id}/historial", response_model=schemas.HistorialOut)
def historial_producto(
    producto_id: int,
    dias: int = Query(30, ge=1, le=365, description="Ventana de días hacia atrás"),
    db: Session = Depends(get_db),
):
    """Devuelve el historial de precios del producto en la ventana indicada."""
    historial = crud.get_historial(db, producto_id, dias)
    if historial is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return historial
