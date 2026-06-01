"""
main.py – API REST de SuperPrecios (FastAPI + SQLAlchemy + PostgreSQL 16).

Endpoints:
  GET /api/productos/buscar          – Búsqueda por nombre (full-text)
  GET /api/productos/{id}/comparar   – Precios actuales en todas las tiendas
  GET /api/productos/{id}/historial  – Historial de precios con filtro de fechas
  GET /api/supermercados             – Lista de supermercados activos
  GET /api/categorias                – Lista de categorías disponibles
  GET /health                        – Health check
"""

from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os

# ── Configuración de la app ───────────────────────────────────────

app = FastAPI(
    title="SuperPrecios API",
    description="API REST para comparación de precios en supermercados de Chile.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # en producción: dominio específico del frontend
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Base de datos ─────────────────────────────────────────────────

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://superprecios_user:superprecios_pass@postgres:5432/superprecios",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Health check ──────────────────────────────────────────────────

@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── Supermercados ─────────────────────────────────────────────────

@app.get("/api/supermercados", tags=["supermercados"])
def listar_supermercados(db: Session = Depends(get_db)):
    """Retorna todos los supermercados activos."""
    rows = db.execute(
        text("SELECT id, nombre, url_base FROM supermercados WHERE activo = TRUE ORDER BY nombre")
    ).fetchall()
    return [{"id": r.id, "nombre": r.nombre, "url_base": r.url_base} for r in rows]


# ── Categorías ────────────────────────────────────────────────────

@app.get("/api/categorias", tags=["productos"])
def listar_categorias(db: Session = Depends(get_db)):
    """Retorna las categorías de productos disponibles."""
    rows = db.execute(
        text("SELECT DISTINCT categoria FROM productos WHERE categoria IS NOT NULL ORDER BY categoria")
    ).fetchall()
    return [r.categoria for r in rows]


# ── Búsqueda de productos ─────────────────────────────────────────

@app.get("/api/productos/buscar", tags=["productos"])
def buscar_productos(
    q: str = Query(..., min_length=2, description="Texto a buscar en nombre de producto"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db),
):
    """
    Búsqueda full-text de productos por nombre.
    Retorna el precio más bajo actual entre todas las tiendas.
    """
    offset = (pagina - 1) * por_pagina

    filtro_categoria = ""
    params: dict = {"q": q, "limit": por_pagina, "offset": offset}

    if categoria:
        filtro_categoria = "AND p.categoria = :categoria"
        params["categoria"] = categoria

    sql = text(f"""
        SELECT
            p.id,
            p.nombre,
            p.categoria,
            p.codigo_barra,
            MIN(v.precio) AS precio_minimo,
            COUNT(DISTINCT v.supermercado_nombre) AS tiendas_disponibles
        FROM productos p
        JOIN v_precios_actuales v ON v.producto_id = p.id  -- usa la vista de precios actuales
        WHERE p.nombre ILIKE '%' || :q || '%'
        {filtro_categoria}
        GROUP BY p.id, p.nombre, p.categoria, p.codigo_barra
        ORDER BY p.nombre
        LIMIT :limit OFFSET :offset
    """)

    # Nota: la vista v_precios_actuales tiene columna producto_id
    # Ajustamos la query para que coincida con el esquema real
    sql_corregida = text(f"""
        SELECT
            p.id,
            p.nombre,
            p.categoria,
            p.codigo_barra,
            MIN(pr.precio) AS precio_minimo,
            COUNT(DISTINCT pr.supermercado_id) AS tiendas_disponibles
        FROM productos p
        JOIN precios pr ON pr.producto_id = p.id
        WHERE p.nombre ILIKE '%' || :q || '%'
        {filtro_categoria}
          AND pr.registrado_en = (
              SELECT MAX(registrado_en)
              FROM precios
              WHERE producto_id = p.id AND supermercado_id = pr.supermercado_id
          )
        GROUP BY p.id, p.nombre, p.categoria, p.codigo_barra
        ORDER BY p.nombre
        LIMIT :limit OFFSET :offset
    """)

    rows = db.execute(sql_corregida, params).fetchall()

    # Total para paginación
    count_sql = text(f"""
        SELECT COUNT(DISTINCT p.id)
        FROM productos p
        JOIN precios pr ON pr.producto_id = p.id
        WHERE p.nombre ILIKE '%' || :q || '%'
        {filtro_categoria}
    """)
    total = db.execute(count_sql, {k: v for k, v in params.items() if k not in ("limit", "offset")}).scalar()

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "resultados": [
            {
                "id": r.id,
                "nombre": r.nombre,
                "categoria": r.categoria,
                "codigo_barra": r.codigo_barra,
                "precio_minimo": float(r.precio_minimo),
                "tiendas_disponibles": r.tiendas_disponibles,
            }
            for r in rows
        ],
    }


# ── Comparación de precios por producto ──────────────────────────

@app.get("/api/productos/{producto_id}/comparar", tags=["precios"])
def comparar_precios(
    producto_id: int,
    db: Session = Depends(get_db),
):
    """
    Retorna el precio más reciente del producto en cada supermercado,
    ordenado de menor a mayor precio.
    """
    # Verificar que el producto existe
    producto = db.execute(
        text("SELECT id, nombre, categoria, codigo_barra FROM productos WHERE id = :id"),
        {"id": producto_id},
    ).fetchone()

    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    sql = text("""
        SELECT DISTINCT ON (pr.supermercado_id)
            s.nombre  AS supermercado,
            s.url_base,
            pr.precio,
            pr.registrado_en
        FROM precios pr
        JOIN supermercados s ON s.id = pr.supermercado_id
        WHERE pr.producto_id = :id
        ORDER BY pr.supermercado_id, pr.registrado_en DESC
    """)
    rows = db.execute(sql, {"id": producto_id}).fetchall()

    precios_ordenados = sorted(rows, key=lambda r: r.precio)

    return {
        "producto": {
            "id": producto.id,
            "nombre": producto.nombre,
            "categoria": producto.categoria,
            "codigo_barra": producto.codigo_barra,
        },
        "comparacion": [
            {
                "supermercado": r.supermercado,
                "precio": float(r.precio),
                "registrado_en": r.registrado_en.isoformat(),
                "es_mas_barato": idx == 0,
            }
            for idx, r in enumerate(precios_ordenados)
        ],
        "precio_minimo": float(precios_ordenados[0].precio) if precios_ordenados else None,
        "precio_maximo": float(precios_ordenados[-1].precio) if precios_ordenados else None,
        "ahorro_maximo": (
            float(precios_ordenados[-1].precio - precios_ordenados[0].precio)
            if len(precios_ordenados) > 1
            else 0.0
        ),
    }


# ── Historial de precios ──────────────────────────────────────────

@app.get("/api/productos/{producto_id}/historial", tags=["precios"])
def historial_precios(
    producto_id: int,
    supermercado: Optional[str] = Query(None, description="Filtrar por supermercado"),
    desde: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    hasta: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Retorna el historial completo de precios de un producto,
    con marca temporal por registro.
    Útil para graficar variaciones en el frontend.
    """
    producto = db.execute(
        text("SELECT id, nombre FROM productos WHERE id = :id"),
        {"id": producto_id},
    ).fetchone()

    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    filtros = ["pr.producto_id = :producto_id"]
    params: dict = {"producto_id": producto_id}

    if supermercado:
        filtros.append("s.nombre ILIKE :supermercado")
        params["supermercado"] = supermercado

    if desde:
        filtros.append("pr.registrado_en >= :desde")
        params["desde"] = datetime.combine(desde, datetime.min.time())

    if hasta:
        filtros.append("pr.registrado_en <= :hasta")
        params["hasta"] = datetime.combine(hasta, datetime.max.time())

    where_clause = " AND ".join(filtros)

    sql = text(f"""
        SELECT
            s.nombre  AS supermercado,
            pr.precio,
            pr.registrado_en
        FROM precios pr
        JOIN supermercados s ON s.id = pr.supermercado_id
        WHERE {where_clause}
        ORDER BY pr.registrado_en ASC
    """)

    rows = db.execute(sql, params).fetchall()

    # Agrupar por supermercado para facilitar el graficado
    historial: dict[str, list] = {}
    for r in rows:
        if r.supermercado not in historial:
            historial[r.supermercado] = []
        historial[r.supermercado].append({
            "precio": float(r.precio),
            "fecha": r.registrado_en.isoformat(),
        })

    return {
        "producto": {"id": producto.id, "nombre": producto.nombre},
        "historial_por_supermercado": historial,
        "total_registros": len(rows),
    }
