"""Publicador de mensajes hacia RabbitMQ usando pika.

Declara un exchange y una cola durables y publica mensajes persistentes, de
modo que el broker conserve los precios aunque el agregador esté caído (uno de
los requisitos del patrón Pub/Sub descritos en el diseño).
"""
from __future__ import annotations

import json
import logging
import time

import pika
from pika.exceptions import AMQPConnectionError

from . import config

logger = logging.getLogger("scraper.publisher")


class RabbitPublisher:
    """Conexión perezosa a RabbitMQ con reintentos y publicación persistente."""

    def __init__(self) -> None:
        self._connection: pika.BlockingConnection | None = None
        self._channel = None

    def connect(self, max_retries: int = 30, retry_delay: float = 2.0) -> None:
        """Abre la conexión y declara la topología, reintentando si hace falta."""
        credentials = pika.PlainCredentials(config.RABBITMQ_USER, config.RABBITMQ_PASSWORD)
        params = pika.ConnectionParameters(
            host=config.RABBITMQ_HOST,
            port=config.RABBITMQ_PORT,
            virtual_host=config.RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )

        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()
                self._declare_topology()
                logger.info("Conectado a RabbitMQ en %s:%s", config.RABBITMQ_HOST, config.RABBITMQ_PORT)
                return
            except AMQPConnectionError as exc:  # broker aún no disponible
                last_error = exc
                logger.warning("RabbitMQ no disponible (intento %s/%s); reintentando…", attempt, max_retries)
                time.sleep(retry_delay)

        raise RuntimeError(f"No fue posible conectar a RabbitMQ: {last_error}")

    def _declare_topology(self) -> None:
        """Declara exchange y cola durables y los enlaza."""
        assert self._channel is not None
        self._channel.exchange_declare(
            exchange=config.PRICES_EXCHANGE, exchange_type="direct", durable=True
        )
        self._channel.queue_declare(queue=config.PRICES_QUEUE, durable=True)
        self._channel.queue_bind(
            queue=config.PRICES_QUEUE,
            exchange=config.PRICES_EXCHANGE,
            routing_key=config.PRICES_ROUTING_KEY,
        )

    def publish(self, message: dict) -> None:
        """Publica un mensaje JSON persistente en el exchange de precios."""
        if self._channel is None or self._connection is None or self._connection.is_closed:
            self.connect()
        assert self._channel is not None

        self._channel.basic_publish(
            exchange=config.PRICES_EXCHANGE,
            routing_key=config.PRICES_ROUTING_KEY,
            body=json.dumps(message, ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,  # mensaje persistente
            ),
        )

    def close(self) -> None:
        if self._connection is not None and self._connection.is_open:
            self._connection.close()
            logger.info("Conexión a RabbitMQ cerrada")
