-- ================================================================
--  SuperPrecios – Inicialización de base de datos PostgreSQL 16
--  Tablas: supermercados, productos, precios
-- ================================================================

-- Tabla supermercados
CREATE TABLE IF NOT EXISTS supermercados (
    id        SERIAL PRIMARY KEY,
    nombre    VARCHAR(50)  NOT NULL UNIQUE,
    url_base  TEXT         NOT NULL,
    activo    BOOLEAN      NOT NULL DEFAULT TRUE
);

-- Tabla productos
CREATE TABLE IF NOT EXISTS productos (
    id           SERIAL PRIMARY KEY,
    nombre       VARCHAR(200) NOT NULL,
    categoria    VARCHAR(100),
    codigo_barra VARCHAR(50)  UNIQUE
);

-- Índice para búsqueda por nombre (full-text insensible a mayúsculas)
CREATE INDEX IF NOT EXISTS idx_productos_nombre
    ON productos USING gin(to_tsvector('spanish', nombre));

-- Tabla precios  (historial completo con marca temporal)
CREATE TABLE IF NOT EXISTS precios (
    id               SERIAL PRIMARY KEY,
    producto_id      INT          NOT NULL REFERENCES productos(id)      ON DELETE CASCADE,
    supermercado_id  INT          NOT NULL REFERENCES supermercados(id)  ON DELETE CASCADE,
    precio           NUMERIC(10,2) NOT NULL,
    registrado_en    TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- Índices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_precios_producto     ON precios(producto_id);
CREATE INDEX IF NOT EXISTS idx_precios_supermercado ON precios(supermercado_id);
CREATE INDEX IF NOT EXISTS idx_precios_fecha        ON precios(registrado_en DESC);

-- Vista: precio más reciente por producto y supermercado
CREATE OR REPLACE VIEW v_precios_actuales AS
SELECT DISTINCT ON (p.producto_id, p.supermercado_id)
    p.id,
    prod.nombre        AS producto_nombre,
    prod.categoria,
    prod.codigo_barra,
    s.nombre           AS supermercado_nombre,
    p.precio,
    p.registrado_en
FROM precios p
JOIN productos    prod ON prod.id = p.producto_id
JOIN supermercados s   ON s.id   = p.supermercado_id
ORDER BY p.producto_id, p.supermercado_id, p.registrado_en DESC;

-- Datos iniciales: supermercados
INSERT INTO supermercados (nombre, url_base, activo) VALUES
    ('Jumbo',    'https://www.jumbo.cl',    TRUE),
    ('Lider',    'https://www.lider.cl',    TRUE),
    ('Unimarc',  'https://www.unimarc.cl',  TRUE)
ON CONFLICT (nombre) DO NOTHING;
