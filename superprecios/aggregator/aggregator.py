"""
aggregator.py – Servicio Agregador de SuperPrecios.

Responsabilidades:
  - Suscribirse a la cola RabbitMQ (patrón Pub/Sub, rol consumidor).
  - Validar cada mensaje con Pydantic.
  - Insertar o actualizar productos en PostgreSQL.
  - Registrar cada precio con marca temporal (historial completo).
  - Reconectar automáticamente ante caídas transitorias del broker.
"""

import json
import logging
import os
import time
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


# ── Conexión a PostgreSQL ─────────────────────────────────────────

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://superprecios_user:superprecios_pass@postgres:5432/superprecios",
)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


# ── Lógica de persistencia ────────────────────────────────────────

def upsert_producto(cur, nombre: str, categoria: str, codigo_barra: Optional[str]) -> int:
    """
    Inserta el producto si no existe (por código de barra o nombre+categoría).
    Retorna el ID del producto.
    """
    if codigo_barra:
        cur.execute(
            """
            INSERT INTO productos (nombre, categoria, codigo_barra)
            VALUES (%s, %s, %s)
            ON CONFLICT (codigo_barra) DO UPDATE
                SET nombre    = EXCLUDED.nombre,
                    categoria = EXCLUDED.categoria
            RETURNING id
            """,
            (nombre, categoria, codigo_barra),
        )
    else:
        cur.execute(
            """
            INSERT INTO productos (nombre, categoria)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (nombre, categoria),
        )
        if cur.rowcount == 0:
            cur.execute(
                "SELECT id FROM productos WHERE nombre = %s AND categoria = %s",
                (nombre, categoria),
            )
    row = cur.fetchone()
    return row[0]


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
    """Valida, persiste y confirma (ACK) un mensaje de la cola."""
    try:
        data = json.loads(body)
        mensaje = PrecioIncoming(**data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Mensaje inválido descartado: %s | Error: %s", body[:120], exc)
        return  # NACK implícito: el mensaje se descarta (no reencola)

    conn = None
    try:
        conn = get_db_connection()
        with conn:
            with conn.cursor() as cur:
                supermercado_id = get_supermercado_id(cur, mensaje.supermercado)
                if supermercado_id is None:
                    logger.warning(
                        "Supermercado '%s' no encontrado o inactivo; mensaje descartado.",
                        mensaje.supermercado,
                    )
                    return

                producto_id = upsert_producto(
                    cur,
                    mensaje.nombre_producto,
                    mensaje.categoria,
                    mensaje.codigo_barra,
                )
                insertar_precio(cur, producto_id, supermercado_id, mensaje.precio)

        logger.debug(
            "Precio persistido: %s | %s | $%.0f",
            mensaje.supermercado, mensaje.nombre_producto, mensaje.precio,
        )
    except Exception as exc:
        logger.error("Error al persistir en PostgreSQL: %s", exc)
        raise   # reencola el mensaje en RabbitMQ
    finally:
        if conn:
            conn.close()


# ── Consumidor RabbitMQ con reconexión automática ─────────────────

RABBITMQ_HOST  = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT  = int(os.getenv("RABBITMQ_PORT", "5672"))
QUEUE_NAME     = os.getenv("RABBITMQ_QUEUE", "precios_queue")
PREFETCH_COUNT = 10   # mensajes procesados en paralelo por el consumidor


def callback(ch, method, properties, body):
    try:
        procesar_mensaje(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        # Reencolar una sola vez para reintentar
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def connect_and_consume(retries: int = 10, delay: int = 5):
    for attempt in range(1, retries + 1):
        try:
            logger.info(
                "Conectando a RabbitMQ %s:%d (intento %d/%d)…",
                RABBITMQ_HOST, RABBITMQ_PORT, attempt, retries,
            )
            params = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=PREFETCH_COUNT)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

            logger.info(
                "Agregador listo – consumiendo cola '%s'…", QUEUE_NAME
            )
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as exc:
            logger.warning("Fallo de conexión: %s", exc)
            if attempt < retries:
                logger.info("Reintentando en %d s…", delay)
                time.sleep(delay)
        except KeyboardInterrupt:
            logger.info("Agregador detenido manualmente.")
            break

    logger.critical(
        "No se pudo conectar a RabbitMQ tras %d intentos. "
        "Servicio detenido.", retries,
    )


if __name__ == "__main__":
    connect_and_consume()
