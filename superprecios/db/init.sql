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


-- ================================================================
--  DATOS DE PRUEBA – permiten validar la API y el frontend
--  antes de que los scrapers hayan ejecutado su primer ciclo.
-- ================================================================

INSERT INTO productos (nombre, categoria, codigo_barra) VALUES
    ('Leche Entera Colun 1L',         'alimentos', '7802900001001'),
    ('Leche Semidescremada Soprole 1L','alimentos', '7802900002002'),
    ('Yogur Natural Nestlé 1kg',       'alimentos', '7802900003003'),
    ('Mantequilla Colun 200g',         'alimentos', '7802900004004'),
    ('Shampoo Head & Shoulders 375ml', 'higiene',   '7509546614797'),
    ('Jabón Dove 90g',                 'higiene',   '7791293021552'),
    ('Pasta de dientes Colgate 75ml',  'higiene',   '7509546034890'),
    ('Detergente Omo 1kg',             'limpieza',  '7891150033954'),
    ('Limpiapisos Fabuloso 1L',        'limpieza',  '7048900009009'),
    ('Esponja Scotch-Brite x3',        'limpieza',  '7048900010010')
ON CONFLICT (codigo_barra) DO NOTHING;

INSERT INTO precios (producto_id, supermercado_id, precio, registrado_en)
SELECT p.id, s.id,
       CASE
           WHEN s.nombre = 'Jumbo'   THEN precio_base
           WHEN s.nombre = 'Lider'   THEN precio_base * 0.95
           WHEN s.nombre = 'Unimarc' THEN precio_base * 1.03
       END,
       NOW() - (random() * interval '2 hours')
FROM (
    VALUES
        ('Leche Entera Colun 1L',          1290),
        ('Leche Semidescremada Soprole 1L', 1390),
        ('Yogur Natural Nestlé 1kg',        2490),
        ('Mantequilla Colun 200g',          2190),
        ('Shampoo Head & Shoulders 375ml',  4990),
        ('Jabón Dove 90g',                   890),
        ('Pasta de dientes Colgate 75ml',   1990),
        ('Detergente Omo 1kg',              4290),
        ('Limpiapisos Fabuloso 1L',         1590),
        ('Esponja Scotch-Brite x3',         1290)
) AS t(nombre_producto, precio_base)
JOIN productos p ON p.nombre = t.nombre_producto
CROSS JOIN supermercados s
ON CONFLICT DO NOTHING;

-- Registros históricos (últimas 48h) para que el gráfico tenga datos
INSERT INTO precios (producto_id, supermercado_id, precio, registrado_en)
SELECT p.id, s.id,
       CASE
           WHEN s.nombre = 'Jumbo'   THEN precio_base * (1 + (random() - 0.5) * 0.08)
           WHEN s.nombre = 'Lider'   THEN precio_base * 0.95 * (1 + (random() - 0.5) * 0.08)
           WHEN s.nombre = 'Unimarc' THEN precio_base * 1.03 * (1 + (random() - 0.5) * 0.08)
       END,
       NOW() - (n * interval '6 hours')
FROM (
    VALUES
        ('Leche Entera Colun 1L',          1290),
        ('Leche Semidescremada Soprole 1L', 1390),
        ('Yogur Natural Nestlé 1kg',        2490),
        ('Shampoo Head & Shoulders 375ml',  4990),
        ('Detergente Omo 1kg',              4290)
) AS t(nombre_producto, precio_base)
JOIN productos p ON p.nombre = t.nombre_producto
CROSS JOIN supermercados s
CROSS JOIN generate_series(1, 8) AS n
ON CONFLICT DO NOTHING;