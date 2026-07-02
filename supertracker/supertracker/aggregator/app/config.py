"""Configuración del Servicio Agregador (lectura desde variables de entorno)."""
from __future__ import annotations

import os

# --- RabbitMQ -------------------------------------------------------------
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "supertracker")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "supertracker")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

PRICES_QUEUE = os.getenv("PRICES_QUEUE", "precios")
PRICES_EXCHANGE = os.getenv("PRICES_EXCHANGE", "precios.exchange")
PRICES_ROUTING_KEY = os.getenv("PRICES_ROUTING_KEY", "precios.nuevo")

# Cuántos mensajes entrega RabbitMQ a este consumidor sin esperar ACK.
# Habilita el balanceo entre múltiples instancias del agregador (competing
# consumers): con prefetch bajo, los mensajes se reparten de forma pareja.
PREFETCH_COUNT = int(os.getenv("PREFETCH_COUNT", "20"))

# --- Base de datos --------------------------------------------------------
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "supertracker")
POSTGRES_USER = os.getenv("POSTGRES_USER", "supertracker")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "supertracker")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

# --- Servidor de salud (FastAPI) -----------------------------------------
HEALTH_HOST = os.getenv("AGGREGATOR_HEALTH_HOST", "0.0.0.0")
HEALTH_PORT = int(os.getenv("AGGREGATOR_HEALTH_PORT", "8001"))
