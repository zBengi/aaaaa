"""
aggregator.py – Servicio Agregador de SuperPrecios.

Une el mismo producto vendido en distintos supermercados en un único registro,
para poder comparar sus precios entre tiendas.

── Algoritmo de deduplicación: TF-IDF (n-gramas de caracteres) + coseno ─────
El problema real: cada supermercado nombra el mismo producto distinto
("Leche Entera Colún 1 L", "Leche Líquida Entera Colún UHT 1L",
"Yoghurt" vs "Yogur"...), y los scrapers no traen un EAN compartido. Un puntaje
difuso fijo no distingue las palabras que importan (marca, variante) de las de
relleno (leche, botella).

Solución (estándar de "record linkage", determinista y sin dependencias de red):
  1. Normalización: minúsculas, sin tildes, unidades unificadas (1 lt→1l),
     sin puntuación, sin palabras de formato (uht, liquida, botella…), tokens
     ordenados alfabéticamente.
  2. Coincidencia exacta sobre el nombre normalizado.
  3. Similitud TF-IDF sobre n-gramas de caracteres (n=3) con distancia coseno:
     los n-gramas poco frecuentes (marca, variante) pesan más que los comunes.
     Se exige, además, que la cantidad coincida cuando ambos la declaran
     (1kg no se une con 3kg). Umbral por defecto: 0.65 (ajustable, ver
     calibrar_matching.py).
  4. Si nada supera el umbral, se crea un producto nuevo.

Se descartó un LLM: por mensaje sería lento, no determinista, caro y añadiría
una dependencia de red frágil en un servicio de streaming.
"""

import json
import logging
import math
import os
import re
import time
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Optional

import pika
import psycopg2
import psycopg2.extras
from pydantic import BaseModel, field_validator, ValidationError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [aggregator] %(levelname)s – %(message)s",
)
logger = logging.getLogger("aggregator")

# Umbral de similitud coseno (0.0–1.0). Más alto = más estricto (menos fusiones).
# Calíbralo con calibrar_matching.py sobre tus datos reales.
UMBRAL_SIMILITUD = float(os.getenv("UMBRAL_SIMILITUD", "0.65"))
NGRAM = 3


# ── Esquema de validación Pydantic ────────────────────────────────

class PrecioIncoming(BaseModel):
    supermercado:    str
    nombre_producto: str
    categoria:       str
    codigo_barra:    Optional[str] = None
    precio:          float
    url_producto:    str
    timestamp:       str

    @field_validator("precio")
    @classmethod
    def precio_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El precio debe ser mayor que cero.")
        return v

    @field_validator("nombre_producto")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre del producto no puede estar vacío.")
        return v.strip()


# ── Normalización de nombres (lógica pura y testeable) ────────────

_UNIDAD_RE = [
    (re.compile(r'(\d+)\s*(?:lt|lts|litros?|l)\b'), r'\1l'),
    (re.compile(r'(\d+)\s*(?:kilos?|kgs?|kg)\b'),    r'\1kg'),
    (re.compile(r'(\d+)\s*(?:grs?|gramos?|g)\b'),    r'\1g'),
    (re.compile(r'(\d+)\s*(?:ml|mililitros?)\b'),    r'\1ml'),
    (re.compile(r'(\d+)\s*cc\b'),                    r'\1ml'),
    (re.compile(r'(?:x|pack(?: de)?)\s*(\d+)\b'),    r'\1un'),
]
# Palabras vacías y de formato que no distinguen el producto.
_STOPWORDS = {
    "de", "el", "la", "los", "las", "un", "una", "con", "sin", "para",
    "uht", "liquida", "botella", "sachet", "pack", "unidad", "und", "u",
    "envase", "formato", "bolsa", "caja", "pote", "tarro",
}
_MEDIDA_RE = re.compile(r'\d+(?:l|kg|g|ml|un)\b')


def normalizar_nombre(nombre: str) -> str:
    """Forma canónica del nombre para comparar entre tiendas."""
    t = nombre.lower().strip()
    t = "".join(c for c in unicodedata.normalize("NFKD", t)
                if not unicodedata.combining(c))
    for rx, rep in _UNIDAD_RE:
        t = rx.sub(rep, t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    tokens = [w for w in t.split() if w not in _STOPWORDS]
    return " ".join(sorted(tokens))          # orden alfabético: ignora el orden de palabras


def extraer_medidas(norm: str) -> frozenset:
    """Cantidades presentes (p. ej. {'1l'} o {'375ml'})."""
    return frozenset(_MEDIDA_RE.findall(norm))


# ── Similitud TF-IDF sobre n-gramas de caracteres + coseno ────────

def _ngrams(s: str, n: int = NGRAM) -> list:
    s = f" {s} "
    return [s[i:i + n] for i in range(len(s) - n + 1)] if len(s) >= n else [s]


def construir_idf(norms: list) -> dict:
    """Calcula el IDF de cada n-grama sobre un corpus de nombres normalizados."""
    N = len(norms)
    df = Counter()
    for s in norms:
        for g in set(_ngrams(s)):
            df[g] += 1
    idf = {g: math.log((N + 1) / (d + 1)) + 1 for g, d in df.items()}
    return {"N": N, "idf": idf}


def vectorizar(s: str, index: dict) -> dict:
    """Vector TF-IDF disperso del nombre `s` según un IDF ya calculado."""
    default = math.log((index["N"] + 1) / 1) + 1   # peso alto para n-gramas nunca vistos
    return {g: c * index["idf"].get(g, default)
            for g, c in Counter(_ngrams(s)).items()}


def coseno(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b[g] for g, v in a.items() if g in b)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


# ── Conexión a PostgreSQL ─────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL es obligatorio (definir en .env.server2).")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def ensure_schema_and_backfill():
    """Migración idempotente: columna nombre_normalizado + índice + re-normaliza
    todos los productos (aplica cambios de lógica sin borrar el volumen)."""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "ALTER TABLE productos "
                    "ADD COLUMN IF NOT EXISTS nombre_normalizado VARCHAR(200)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_productos_norm "
                    "ON productos (categoria, nombre_normalizado)"
                )
                cur.execute("SELECT id, nombre FROM productos")
                filas = cur.fetchall()
                for pid, nombre in filas:
                    cur.execute(
                        "UPDATE productos SET nombre_normalizado = %s WHERE id = %s",
                        (normalizar_nombre(nombre), pid),
                    )
        logger.info("Backfill: %d productos (re)normalizados.", len(filas))
    finally:
        conn.close()


# ── Índice de catálogo por categoría (con IDF reconstruido al vuelo) ─
# El agregador es un consumidor de un solo hilo → esta caché es consistente.

_cat: dict[str, dict] = {}   # categoria -> {norm2id, ids, norms, index, vecs, dirty}


def _cargar_categoria(cur, categoria: str) -> dict:
    if categoria not in _cat:
        cur.execute(
            "SELECT id, nombre_normalizado FROM productos "
            "WHERE categoria = %s AND nombre_normalizado IS NOT NULL",
            (categoria,),
        )
        ids, norms, norm2id = [], [], {}
        for pid, norm in cur.fetchall():
            ids.append(pid); norms.append(norm); norm2id[norm] = pid
        _cat[categoria] = {"norm2id": norm2id, "ids": ids, "norms": norms,
                           "index": None, "vecs": {}, "dirty": True}
    return _cat[categoria]


def _reconstruir_index(entry: dict):
    """Recalcula IDF y los vectores TF-IDF de la categoría (sólo si cambió)."""
    entry["index"] = construir_idf(entry["norms"])
    entry["vecs"] = {
        pid: vectorizar(norm, entry["index"])
        for pid, norm in zip(entry["ids"], entry["norms"])
    }
    entry["dirty"] = False


# ── Resolución de identidad del producto ──────────────────────────

def resolver_producto_id(cur, nombre: str, categoria: str,
                         codigo_barra: Optional[str]) -> int:
    norm = normalizar_nombre(nombre)
    entry = _cargar_categoria(cur, categoria)

    # 1) coincidencia exacta sobre el nombre normalizado
    if norm in entry["norm2id"]:
        return entry["norm2id"][norm]

    # 2) similitud TF-IDF + coseno (con candado de medida)
    if entry["ids"]:
        if entry["dirty"]:
            _reconstruir_index(entry)
        medidas = extraer_medidas(norm)
        qv = vectorizar(norm, entry["index"])
        mejor_id, mejor_score = None, 0.0
        for pid, cnorm in zip(entry["ids"], entry["norms"]):
            mc = extraer_medidas(cnorm)
            if medidas and mc and medidas != mc:      # 1kg ≠ 3kg
                continue
            s = coseno(qv, entry["vecs"][pid])
            if s > mejor_score:
                mejor_score, mejor_id = s, pid
        if mejor_id is not None and mejor_score >= UMBRAL_SIMILITUD:
            return mejor_id

    # 3) producto nuevo
    cur.execute(
        """
        INSERT INTO productos (nombre, categoria, codigo_barra, nombre_normalizado)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (nombre, categoria, codigo_barra, norm),
    )
    nuevo_id = cur.fetchone()[0]
    entry["ids"].append(nuevo_id)
    entry["norms"].append(norm)
    entry["norm2id"][norm] = nuevo_id
    entry["dirty"] = True            # el IDF se recalcula en la próxima búsqueda
    logger.info("Nuevo producto #%d: %s [%s]", nuevo_id, nombre, categoria)
    return nuevo_id


def get_supermercado_id(cur, nombre: str) -> Optional[int]:
    cur.execute(
        "SELECT id FROM supermercados WHERE nombre = %s AND activo = TRUE",
        (nombre,),
    )
    row = cur.fetchone()
    return row[0] if row else None


def insertar_precio(cur, producto_id: int, supermercado_id: int, precio: float):
    cur.execute(
        """
        INSERT INTO precios (producto_id, supermercado_id, precio, registrado_en)
        VALUES (%s, %s, %s, %s)
        """,
        (producto_id, supermercado_id, precio, datetime.utcnow()),
    )


def procesar_mensaje(body: bytes):
    try:
        data = json.loads(body)
        mensaje = PrecioIncoming(**data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Mensaje inválido descartado: %s | Error: %s", body[:120], exc)
        return

    conn = None
    try:
        conn = get_db_connection()
        with conn:
            with conn.cursor() as cur:
                supermercado_id = get_supermercado_id(cur, mensaje.supermercado)
                if supermercado_id is None:
                    logger.warning(
                        "Supermercado '%s' no encontrado o inactivo; descartado.",
                        mensaje.supermercado,
                    )
                    return
                producto_id = resolver_producto_id(
                    cur, mensaje.nombre_producto, mensaje.categoria, mensaje.codigo_barra,
                )
                insertar_precio(cur, producto_id, supermercado_id, mensaje.precio)
    except Exception as exc:
        logger.error("Error al persistir en PostgreSQL: %s", exc)
        raise
    finally:
        if conn:
            conn.close()


# ── Consumidor RabbitMQ con reconexión automática ─────────────────

RABBITMQ_HOST  = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT  = int(os.getenv("RABBITMQ_PORT", "5672"))
QUEUE_NAME     = os.getenv("RABBITMQ_QUEUE", "precios_queue")
PREFETCH_COUNT = 10

# Credenciales — usuario dedicado de solo consumo (NO el admin, NO "guest").
_RABBITMQ_USER = os.getenv("RABBITMQ_CONSUMER_USER")
_RABBITMQ_PASS = os.getenv("RABBITMQ_CONSUMER_PASS")
if not _RABBITMQ_USER or not _RABBITMQ_PASS:
    raise RuntimeError(
        "RABBITMQ_CONSUMER_USER y RABBITMQ_CONSUMER_PASS son obligatorios "
        "(definir en .env.server2, no usar 'guest')."
    )
RABBITMQ_CREDENTIALS = pika.PlainCredentials(_RABBITMQ_USER, _RABBITMQ_PASS)


def callback(ch, method, properties, body):
    try:
        procesar_mensaje(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def connect_and_consume(retries: int = 10, delay: int = 5):
    for intento in range(1, retries + 1):
        try:
            ensure_schema_and_backfill()
            break
        except Exception as exc:
            logger.warning("DB no lista (%d/%d): %s", intento, retries, exc)
            time.sleep(delay)

    for attempt in range(1, retries + 1):
        try:
            logger.info("Conectando a RabbitMQ %s:%d (intento %d/%d)…",
                        RABBITMQ_HOST, RABBITMQ_PORT, attempt, retries)
            params = pika.ConnectionParameters(
                host=RABBITMQ_HOST, port=RABBITMQ_PORT,
                credentials=RABBITMQ_CREDENTIALS,
                heartbeat=600, blocked_connection_timeout=300,
            )
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=PREFETCH_COUNT)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            logger.info("Agregador listo – consumiendo cola '%s'…", QUEUE_NAME)
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as exc:
            logger.warning("Fallo de conexión: %s", exc)
            if attempt < retries:
                time.sleep(delay)
        except KeyboardInterrupt:
            logger.info("Agregador detenido manualmente.")
            break

    logger.critical("No se pudo conectar a RabbitMQ tras %d intentos.", retries)


if __name__ == "__main__":
    connect_and_consume()