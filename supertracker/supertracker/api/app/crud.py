"""Consultas de la API REST.

Las consultas analíticas (último precio por tienda, comparativa, historial)
se escriben en SQL con DISTINCT ON de PostgreSQL para obtener de forma
eficiente la lectura más reciente por (producto, supermercado).
"""
from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from . import models, schemas


# --------------------------------------------------------------- catálogos
def list_supermercados(db: Session) -> list[schemas.SupermercadoOut]:
    rows = db.execute(
        select(models.Supermercado).order_by(models.Supermercado.nombre)
    ).scalars().all()
    return [schemas.SupermercadoOut.model_validate(r) for r in rows]


def list_categorias(db: Session) -> list[str]:
    rows = db.execute(
        text("SELECT DISTINCT categoria FROM producto ORDER BY categoria")
    ).all()
    return [r[0] for r in rows]


# ----------------------------------------------------------- búsqueda lista
_SEARCH_SQL = text(
    """
    WITH ultimos AS (
        SELECT DISTINCT ON (p.producto_id, p.supermercado_id)
            p.producto_id,
            p.supermercado_id,
            s.nombre AS supermercado_nombre,
            LEAST(p.precio, COALESCE(p.precio_oferta, p.precio)) AS precio_efectivo,
            p.registrado_en
        FROM precio p
        JOIN supermercado s ON s.id = p.supermercado_id AND s.activo = TRUE
        ORDER BY p.producto_id, p.supermercado_id, p.registrado_en DESC
    )
    SELECT
        pr.id,
        pr.nombre,
        pr.categoria,
        MIN(u.precio_efectivo)                                        AS precio_min,
        MAX(u.precio_efectivo)                                        AS precio_max,
        COUNT(u.supermercado_id)                                      AS n_tiendas,
        MAX(u.registrado_en)                                          AS ultima_actualizacion,
        (ARRAY_AGG(u.supermercado_nombre ORDER BY u.precio_efectivo ASC))[1] AS sm_mas_barato
    FROM producto pr
    LEFT JOIN ultimos u ON u.producto_id = pr.id
    WHERE (CAST(:q AS text) IS NULL OR pr.nombre ILIKE :q_like)
      AND (CAST(:categoria AS text) IS NULL OR pr.categoria = :categoria)
    GROUP BY pr.id, pr.nombre, pr.categoria
    ORDER BY pr.nombre
    LIMIT :limit OFFSET :offset
    """
)

_COUNT_SQL = text(
    """
    SELECT COUNT(*) FROM producto pr
    WHERE (CAST(:q AS text) IS NULL OR pr.nombre ILIKE :q_like)
      AND (CAST(:categoria AS text) IS NULL OR pr.categoria = :categoria)
    """
)


def search_productos(
    db: Session,
    q: str | None,
    categoria: str | None,
    page: int,
    page_size: int,
) -> schemas.PaginatedProductos:
    q_like = f"%{q}%" if q else None
    params = {
        "q": q,
        "q_like": q_like,
        "categoria": categoria,
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }

    total = db.execute(_COUNT_SQL, params).scalar_one()
    rows = db.execute(_SEARCH_SQL, params).mappings().all()

    items = [
        schemas.ProductoResumen(
            id=r["id"],
            nombre=r["nombre"],
            categoria=r["categoria"],
            precio_min=float(r["precio_min"]) if r["precio_min"] is not None else None,
            precio_max=float(r["precio_max"]) if r["precio_max"] is not None else None,
            supermercado_mas_barato=r["sm_mas_barato"],
            n_tiendas=r["n_tiendas"],
            ahorro=(
                float(r["precio_max"]) - float(r["precio_min"])
                if r["precio_min"] is not None and r["precio_max"] is not None
                else None
            ),
            ultima_actualizacion=r["ultima_actualizacion"],
        )
        for r in rows
    ]
    return schemas.PaginatedProductos(total=total, page=page, page_size=page_size, items=items)


# ---------------------------------------------------------------- detalle
def get_producto(db: Session, producto_id: int) -> models.Producto | None:
    return db.get(models.Producto, producto_id)


_COMPARATIVA_SQL = text(
    """
    SELECT DISTINCT ON (p.supermercado_id)
        p.supermercado_id,
        s.nombre AS supermercado_nombre,
        p.precio,
        p.precio_oferta,
        LEAST(p.precio, COALESCE(p.precio_oferta, p.precio)) AS precio_efectivo,
        p.url_producto,
        p.registrado_en
    FROM precio p
    JOIN supermercado s ON s.id = p.supermercado_id AND s.activo = TRUE
    WHERE p.producto_id = :pid
    ORDER BY p.supermercado_id, p.registrado_en DESC
    """
)


def get_comparativa(db: Session, producto_id: int) -> schemas.ComparativaOut | None:
    producto = db.get(models.Producto, producto_id)
    if producto is None:
        return None

    rows = db.execute(_COMPARATIVA_SQL, {"pid": producto_id}).mappings().all()
    precios = [
        schemas.PrecioEnTienda(
            supermercado_id=r["supermercado_id"],
            supermercado_nombre=r["supermercado_nombre"],
            precio=float(r["precio"]),
            precio_oferta=float(r["precio_oferta"]) if r["precio_oferta"] is not None else None,
            precio_efectivo=float(r["precio_efectivo"]),
            url_producto=r["url_producto"],
            registrado_en=r["registrado_en"],
        )
        for r in rows
    ]
    precios.sort(key=lambda x: x.precio_efectivo)  # más barato primero
    mejor = precios[0] if precios else None

    return schemas.ComparativaOut(
        producto=schemas.ProductoDetalle.model_validate(producto),
        precios=precios,
        mejor_precio=mejor,
    )


_HISTORIAL_SQL = text(
    """
    SELECT
        s.nombre AS supermercado_nombre,
        p.precio,
        p.precio_oferta,
        p.registrado_en
    FROM precio p
    JOIN supermercado s ON s.id = p.supermercado_id
    WHERE p.producto_id = :pid
      AND p.registrado_en >= NOW() - make_interval(days => :dias)
    ORDER BY p.registrado_en ASC
    """
)


def get_historial(db: Session, producto_id: int, dias: int) -> schemas.HistorialOut | None:
    producto = db.get(models.Producto, producto_id)
    if producto is None:
        return None

    rows = db.execute(_HISTORIAL_SQL, {"pid": producto_id, "dias": dias}).mappings().all()
    puntos = [
        schemas.HistorialPunto(
            supermercado_nombre=r["supermercado_nombre"],
            precio=float(r["precio"]),
            precio_oferta=float(r["precio_oferta"]) if r["precio_oferta"] is not None else None,
            registrado_en=r["registrado_en"],
        )
        for r in rows
    ]
    return schemas.HistorialOut(
        producto_id=producto.id,
        producto_nombre=producto.nombre,
        dias=dias,
        puntos=puntos,
    )


# ------------------------------------------------------------------ stats
_STATS_SQL = text(
    """
    SELECT
        (SELECT COUNT(*) FROM producto)        AS total_productos,
        (SELECT COUNT(*) FROM supermercado)    AS total_supermercados,
        (SELECT COUNT(*) FROM precio)          AS total_registros_precio,
        (SELECT MAX(registrado_en) FROM precio) AS ultima_actualizacion
    """
)


def get_stats(db: Session) -> schemas.StatsOut:
    r = db.execute(_STATS_SQL).mappings().one()
    return schemas.StatsOut(
        total_productos=r["total_productos"],
        total_supermercados=r["total_supermercados"],
        total_registros_precio=r["total_registros_precio"],
        ultima_actualizacion=r["ultima_actualizacion"],
    )
