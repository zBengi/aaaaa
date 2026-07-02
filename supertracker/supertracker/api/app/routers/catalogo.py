"""Endpoints de supermercados, categorías y estadísticas."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..db import get_db

router = APIRouter(tags=["catálogo"])


@router.get("/supermercados", response_model=list[schemas.SupermercadoOut])
def listar_supermercados(db: Session = Depends(get_db)):
    """Lista las cadenas de supermercado registradas."""
    return crud.list_supermercados(db)


@router.get("/categorias", response_model=list[str])
def listar_categorias(db: Session = Depends(get_db)):
    """Lista las categorías disponibles (para filtrar la búsqueda)."""
    return crud.list_categorias(db)


@router.get("/stats", response_model=schemas.StatsOut)
def estadisticas(db: Session = Depends(get_db)):
    """Métricas generales del sistema para el panel del frontend."""
    return crud.get_stats(db)
