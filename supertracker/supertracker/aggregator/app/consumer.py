"""Consumidor de RabbitMQ del Servicio Agregador.

Se suscribe a la cola de precios, valida cada mensaje con Pydantic y lo
persiste. Confirma (ACK) los mensajes procesados y rechaza sin reencolar
(NACK requeue=False) los mensajes inválidos, evitando bucles de "poison
message". Mantiene contadores expuestos por el endpoint de métricas.
"""
from __future__ import annotations

import json
import logging
import time

import pika
from pika.exceptions import AMQPConnectionError, ChannelClosedByBroker
from pydantic import ValidationError

from . import config
from .db import SessionLocal
from .repository import persist_price
from .schemas import IncomingPrice

logger = logging.getLogger("aggregator.consumer")

# Estado compartido con el servidor de salud/métricas.
STATS = {"processed": 0, "failed": 0, "last_error": None, "started_at": time.time()}


def _on_message(channel, method, _properties, body: bytes) -> None:
    try:
        payload = json.loads(body.decode("utf-8"))
        msg = IncomingPrice(**payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        STATS["failed"] += 1
        STATS["last_error"] = str(exc)
        logger.warning("Mensaje inválido descartado: %s", exc)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    session = SessionLocal()
    try:
        persist_price(session, msg)
        STATS["processed"] += 1
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:  # error transitorio de BD → reencolar
        session.rollback()
        STATS["failed"] += 1
        STATS["last_error"] = str(exc)
        logger.exception("Error al persistir; el mensaje se reencola")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        time.sleep(1)  # backoff suave para no saturar ante caídas de BD
    finally:
        session.close()


def run_consumer() -> None:
    """Bucle principal del consumidor con reconexión automática."""
    credentials = pika.PlainCredentials(config.RABBITMQ_USER, config.RABBITMQ_PASSWORD)
    params = pika.ConnectionParameters(
        host=config.RABBITMQ_HOST,
        port=config.RABBITMQ_PORT,
        virtual_host=config.RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300,
    )

    while True:
        try:
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            # Declara la misma topología durable que el publicador.
            channel.exchange_declare(exchange=config.PRICES_EXCHANGE, exchange_type="direct", durable=True)
            channel.queue_declare(queue=config.PRICES_QUEUE, durable=True)
            channel.queue_bind(
                queue=config.PRICES_QUEUE,
                exchange=config.PRICES_EXCHANGE,
                routing_key=config.PRICES_ROUTING_KEY,
            )

            # Reparte la carga entre instancias del agregador.
            channel.basic_qos(prefetch_count=config.PREFETCH_COUNT)
            channel.basic_consume(queue=config.PRICES_QUEUE, on_message_callback=_on_message)

            logger.info("Agregador escuchando la cola '%s'…", config.PRICES_QUEUE)
            channel.start_consuming()

        except (AMQPConnectionError, ChannelClosedByBroker):
            logger.warning("Conexión con RabbitMQ perdida; reintentando en 3 s…")
            time.sleep(3)
        except KeyboardInterrupt:
            logger.info("Consumidor detenido por el usuario")
            break
