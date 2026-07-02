-- =====================================================================
-- SuperTracker — Esquema de base de datos (PostgreSQL 16)
-- Sistema Distribuido para Comparación de Precios en Supermercados
-- Universidad Austral de Chile — INFO288
--
-- Este script se ejecuta automáticamente la primera vez que arranca el
-- contenedor de PostgreSQL (carpeta /docker-entrypoint-initdb.d).
-- Refleja exactamente el diccionario de datos del documento de diseño.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Tabla: supermercado
-- Cadenas de supermercado monitorizadas. Una fila por cadena.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS supermercado (
    id        SERIAL       PRIMARY KEY,
    nombre    VARCHAR(50)  NOT NULL UNIQUE,   -- Jumbo / Líder / Unimarc
    url_base  VARCHAR(200) NOT NULL,          -- URL raíz del sitio a scrapear
    activo    BOOLEAN      NOT NULL DEFAULT TRUE  -- Habilita/inhabilita el scraper
);

COMMENT ON TABLE  supermercado            IS 'Cadenas de supermercado monitorizadas por el sistema';
COMMENT ON COLUMN supermercado.nombre     IS 'Nombre único de la cadena (clave natural usada por el agregador)';
COMMENT ON COLUMN supermercado.url_base   IS 'URL raíz del sitio web a scrapear';
COMMENT ON COLUMN supermercado.activo     IS 'Indica si el scraper de esta cadena está activo';

-- ---------------------------------------------------------------------
-- Tabla: producto
-- Catálogo de productos. El nombre es la clave natural con que el
-- agregador identifica un producto entre distintas cadenas.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS producto (
    id          SERIAL        PRIMARY KEY,
    nombre      VARCHAR(200)  NOT NULL UNIQUE,  -- Nombre del producto tal como aparece en el sitio
    categoria   VARCHAR(100)  NOT NULL,         -- lácteo, bebida, higiene, etc.
    descripcion TEXT          NULL,             -- Descripción adicional opcional
    creado_en   TIMESTAMP     NOT NULL DEFAULT NOW()  -- Primer registro del producto
);

COMMENT ON TABLE  producto             IS 'Catálogo unificado de productos monitorizados';
COMMENT ON COLUMN producto.nombre      IS 'Nombre del producto (clave natural usada por el agregador para deduplicar)';
COMMENT ON COLUMN producto.categoria   IS 'Categoría del producto (alimento, higiene, limpieza, etc.)';
COMMENT ON COLUMN producto.descripcion IS 'Descripción adicional del producto, puede ser NULL';
COMMENT ON COLUMN producto.creado_en   IS 'Fecha/hora del primer registro del producto en el sistema';

-- ---------------------------------------------------------------------
-- Tabla: precio
-- Historial de precios. Se inserta una fila por cada lectura de scraping
-- (append-only), lo que habilita las consultas históricas.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS precio (
    id              SERIAL         PRIMARY KEY,
    producto_id     INTEGER        NOT NULL REFERENCES producto(id)     ON DELETE CASCADE,
    supermercado_id INTEGER        NOT NULL REFERENCES supermercado(id) ON DELETE CASCADE,
    precio          NUMERIC(10,2)  NOT NULL CHECK (precio >= 0),  -- Precio en CLP
    precio_oferta   NUMERIC(10,2)  NULL     CHECK (precio_oferta IS NULL OR precio_oferta >= 0),
    url_producto    VARCHAR(500)   NOT NULL, -- URL directa al producto en el sitio
    registrado_en   TIMESTAMP      NOT NULL DEFAULT NOW()  -- Marca temporal de la lectura
);

COMMENT ON TABLE  precio               IS 'Historial append-only de precios (una fila por lectura de scraping)';
COMMENT ON COLUMN precio.producto_id     IS 'FK al producto';
COMMENT ON COLUMN precio.supermercado_id IS 'FK al supermercado';
COMMENT ON COLUMN precio.precio          IS 'Precio normal en pesos chilenos (CLP)';
COMMENT ON COLUMN precio.precio_oferta   IS 'Precio con descuento si existe, NULL si no hay oferta';
COMMENT ON COLUMN precio.url_producto    IS 'URL directa al producto en el sitio del supermercado';
COMMENT ON COLUMN precio.registrado_en   IS 'Fecha/hora exacta en que se registró este precio';

-- ---------------------------------------------------------------------
-- Índices
-- Soportan: búsqueda de productos por nombre/categoría, comparación de
-- precios por producto, y consultas de historial ordenadas por fecha.
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_producto_nombre        ON producto (nombre);
CREATE INDEX IF NOT EXISTS idx_producto_categoria     ON producto (categoria);

CREATE INDEX IF NOT EXISTS idx_precio_producto        ON precio (producto_id);
CREATE INDEX IF NOT EXISTS idx_precio_supermercado    ON precio (supermercado_id);
CREATE INDEX IF NOT EXISTS idx_precio_registrado_en   ON precio (registrado_en DESC);

-- Índice compuesto que acelera "último precio por (producto, supermercado)"
CREATE INDEX IF NOT EXISTS idx_precio_prod_super_fecha
    ON precio (producto_id, supermercado_id, registrado_en DESC);

-- ---------------------------------------------------------------------
-- Datos semilla: las tres cadenas del alcance de la Iteración 1.
-- El agregador igualmente crea cadenas faltantes de forma idempotente,
-- pero precargarlas deja el sistema listo desde el primer arranque.
-- ---------------------------------------------------------------------
INSERT INTO supermercado (nombre, url_base, activo) VALUES
    ('Jumbo',   'https://www.jumbo.cl',   TRUE),
    ('Líder',   'https://www.lider.cl',   TRUE),
    ('Unimarc', 'https://www.unimarc.cl', TRUE)
ON CONFLICT (nombre) DO NOTHING;
