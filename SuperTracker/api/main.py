"""
main.py – API REST de SuperPrecios (FastAPI + SQLAlchemy + PostgreSQL 16).

Endpoints:
  GET /api/productos/buscar          – Búsqueda por nombre (por palabras, AND)
  GET /api/productos/{id}/comparar   – Precios actuales en todas las tiendas
  GET /api/productos/{id}/historial  – Historial de precios con filtro de fechas
  GET /api/supermercados             – Lista de supermercados activos
  GET /api/categorias                – Lista de categorías disponibles
  GET /health                        – Health check
"""

import os
import unicodedata
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# ── Configuración de la app ───────────────────────────────────────

app = FastAPI(
    title="SuperPrecios API",
    description="API REST para comparación de precios en supermercados de Chile.",
    version="1.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS — lista explícita de orígenes vía entorno, nunca "*" en producción.
_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
if not _cors_origins:
    # Fallback solo para desarrollo local
    _cors_origins = ["http://localhost:5173", "http://localhost"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Rate limiting — protege /api/productos/buscar (LIKE con full scan) de abuso/DoS.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Cabeceras de seguridad básicas en cada respuesta (defensa en profundidad;
# Traefik/Nginx ya agregan las suyas, pero así queda cubierto igual si la
# API se expone directo alguna vez).
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# ── Base de datos ─────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL es obligatorio (definir en .env.server2).")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Utilidad de búsqueda: normalizar texto (minúsculas + sin tildes) ─
# Debe coincidir con la normalización que aplica el SQL más abajo.

def _normalizar_busqueda(texto: str) -> str:
    t = "".join(
        c for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )
    return t.lower().strip()


# SQL que normaliza la columna igual que _normalizar_busqueda():
# quita tildes (mayúsculas y minúsculas) y pasa a minúsculas.
_COL_NORM = "lower(translate(p.nombre, 'ÁÉÍÓÚÜÑáéíóúüñ', 'AEIOUUNaeiouun'))"


# ── Health check ──────────────────────────────────────────────────

@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── Supermercados ─────────────────────────────────────────────────

@app.get("/api/supermercados", tags=["supermercados"])
def listar_supermercados(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id, nombre, url_base FROM supermercados WHERE activo = TRUE ORDER BY nombre")
    ).fetchall()
    return [{"id": r.id, "nombre": r.nombre, "url_base": r.url_base} for r in rows]


# ── Categorías ────────────────────────────────────────────────────

@app.get("/api/categorias", tags=["productos"])
def listar_categorias(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT DISTINCT categoria FROM productos WHERE categoria IS NOT NULL ORDER BY categoria")
    ).fetchall()
    return [r.categoria for r in rows]


# ── Búsqueda de productos ─────────────────────────────────────────

@app.get("/api/productos/buscar", tags=["productos"])
@limiter.limit("20/minute")
def buscar_productos(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100, description="Texto a buscar en nombre de producto"),
    categoria: Optional[str] = Query(None, max_length=100, description="Filtrar por categoría"),
    pagina: int = Query(1, ge=1, le=1000, description="Número de página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db),
):
    """
    Búsqueda por palabras: cada palabra buscada debe aparecer en el nombre del
    producto (en cualquier orden y posición), sin distinguir mayúsculas ni tildes.
    Ej.: "leche loncoleche" encuentra "Leche Entera Loncoleche Sin Tapa 1L".
    Retorna el precio más bajo actual entre todas las tiendas.
    """
    offset = (pagina - 1) * por_pagina

    # 1) separar la consulta en palabras normalizadas (sin tildes, minúsculas)
    tokens = [t for t in _normalizar_busqueda(q).split() if t]
    if not tokens:
        tokens = [_normalizar_busqueda(q)]

    # 2) una condición LIKE por palabra, unidas con AND (todas deben estar).
    #    Los valores van SIEMPRE como parámetros (sin inyección SQL).
    cond_tokens = " AND ".join(f"{_COL_NORM} LIKE :tok{i}" for i in range(len(tokens)))
    params: dict = {f"tok{i}": f"%{tok}%" for i, tok in enumerate(tokens)}
    params["frase"] = f"%{_normalizar_busqueda(q)}%"   # para priorizar coincidencia exacta
    params.update({"limit": por_pagina, "offset": offset})

    filtro_categoria = ""
    if categoria:
        filtro_categoria = "AND p.categoria = :categoria"
        params["categoria"] = categoria

    sql = text(f"""
        SELECT
            p.id,
            p.nombre,
            p.categoria,
            p.codigo_barra,
            MIN(pr.precio) AS precio_minimo,
            COUNT(DISTINCT pr.supermercado_id) AS tiendas_disponibles
        FROM productos p
        JOIN precios pr ON pr.producto_id = p.id
        WHERE {cond_tokens}
        {filtro_categoria}
          AND pr.registrado_en = (
              SELECT MAX(registrado_en)
              FROM precios
              WHERE producto_id = p.id AND supermercado_id = pr.supermercado_id
          )
        GROUP BY p.id, p.nombre, p.categoria, p.codigo_barra
        ORDER BY
            ({_COL_NORM} LIKE :frase) DESC,   -- primero los que traen la frase completa
            length(p.nombre) ASC,             -- luego los nombres más cortos (más precisos)
            p.nombre ASC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(sql, params).fetchall()

    # 3) total para paginación (mismas condiciones, sin límites)
    count_sql = text(f"""
        SELECT COUNT(DISTINCT p.id)
        FROM productos p
        WHERE {cond_tokens}
        {filtro_categoria}
    """)
    count_params = {k: v for k, v in params.items()
                    if k not in ("limit", "offset", "frase")}
    total = db.execute(count_sql, count_params).scalar()

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
def comparar_precios(producto_id: int, db: Session = Depends(get_db)):
    """Precio más reciente del producto en cada supermercado, de menor a mayor."""
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
            if len(precios_ordenados) > 1 else 0.0
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
    """Historial completo de precios de un producto, agrupado por supermercado."""
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
        SELECT s.nombre AS supermercado, pr.precio, pr.registrado_en
        FROM precios pr
        JOIN supermercados s ON s.id = pr.supermercado_id
        WHERE {where_clause}
        ORDER BY pr.registrado_en ASC
    """)
    rows = db.execute(sql, params).fetchall()

    historial: dict[str, list] = {}
    for r in rows:
        historial.setdefault(r.supermercado, []).append({
            "precio": float(r.precio),
            "fecha": r.registrado_en.isoformat(),
        })

    return {
        "producto": {"id": producto.id, "nombre": producto.nombre},
        "historial_por_supermercado": historial,
        "total_registros": len(rows),
    }