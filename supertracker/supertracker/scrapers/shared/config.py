"""Configuración central de los scrapers.

Toda la configuración se lee desde variables de entorno para cumplir con el
principio de los Doce Factores y permitir el despliegue en contenedores sin
modificar el código. Los valores por defecto permiten ejecutar en local.
"""
from __future__ import annotations

import os


def _get_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# --- RabbitMQ -------------------------------------------------------------
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "supertracker")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "supertracker")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

# Cola y exchange donde se publican los precios.
PRICES_QUEUE = os.getenv("PRICES_QUEUE", "precios")
PRICES_EXCHANGE = os.getenv("PRICES_EXCHANGE", "precios.exchange")
PRICES_ROUTING_KEY = os.getenv("PRICES_ROUTING_KEY", "precios.nuevo")

# --- Scraping -------------------------------------------------------------
# "mock"  -> genera precios sintéticos a partir de un catálogo semilla.
#            Garantiza un demo reproducible de extremo a extremo sin depender
#            de la estructura HTML (cambiante) ni del anti-bot de los sitios.
# "real"  -> realiza peticiones HTTP reales con requests + BeautifulSoup.
SCRAPER_MODE = os.getenv("SCRAPER_MODE", "mock").strip().lower()

# Scraping responsable: delay entre peticiones y User-Agent válido.
SCRAPER_DELAY_SECONDS = float(os.getenv("SCRAPER_DELAY_SECONDS", "1.5"))
SCRAPER_USER_AGENT = os.getenv(
    "SCRAPER_USER_AGENT",
    "SuperTrackerBot/1.0 (+https://github.com/uach-info288/supertracker)",
)
SCRAPER_TIMEOUT_SECONDS = float(os.getenv("SCRAPER_TIMEOUT_SECONDS", "10"))

# Tope de productos por tienda (límite declarado en el diseño: 500).
MAX_PRODUCTS_PER_STORE = int(os.getenv("MAX_PRODUCTS_PER_STORE", "500"))

# --- Scheduler ------------------------------------------------------------
# Intervalo entre corridas de scraping. Por defecto cada 1 hora (diseño).
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "60"))
# Ejecutar una corrida inmediatamente al iniciar (útil para el demo).
RUN_ON_STARTUP = _get_bool("RUN_ON_STARTUP", True)

# Identifica al scraper concreto (jumbo / lider / unimarc). Lo fija cada
# servicio en docker-compose mediante la variable STORE.
STORE = os.getenv("STORE", "jumbo").strip().lower()
