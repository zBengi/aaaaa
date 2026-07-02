"""Clase base de los scrapers.

Centraliza el flujo común: obtener productos, construir mensajes válidos y
publicarlos en RabbitMQ. Cada scraper concreto (Jumbo, Líder, Unimarc) hereda
de aquí y aporta sus selectores reales y un factor de precio para el modo mock.

Diseño desacoplado: el scraper sólo conoce el contrato del mensaje y el
publicador; no sabe quién consume sus datos (patrón Pub/Sub).
"""
from __future__ import annotations

import abc
import logging
import random
import time

import requests
from bs4 import BeautifulSoup

from .catalog import CATALOG
from .config import (
    MAX_PRODUCTS_PER_STORE,
    SCRAPER_DELAY_SECONDS,
    SCRAPER_MODE,
    SCRAPER_TIMEOUT_SECONDS,
    SCRAPER_USER_AGENT,
)
from .message import PriceMessage
from .publisher import RabbitPublisher

logger = logging.getLogger("scraper.base")


class BaseScraper(abc.ABC):
    """Plantilla común para los scrapers de cada cadena."""

    #: Nombre de la cadena (Jumbo / Líder / Unimarc).
    store_name: str = ""
    #: URL raíz del sitio.
    url_base: str = ""
    #: Factor de precio aplicado en modo mock para diferenciar tiendas.
    price_factor: float = 1.0

    def __init__(self, publisher: RabbitPublisher) -> None:
        self.publisher = publisher
        self.scraper_id = f"scraper-{self.store_name.lower()}"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": SCRAPER_USER_AGENT})

    # ------------------------------------------------------------------ API
    def run_once(self) -> int:
        """Ejecuta una corrida completa de scraping y publica los precios."""
        logger.info("[%s] Iniciando corrida en modo '%s'", self.store_name, SCRAPER_MODE)
        try:
            items = self._scrape_real() if SCRAPER_MODE == "real" else self._scrape_mock()
        except Exception:  # una corrida fallida no debe tumbar el proceso
            logger.exception("[%s] Error durante el scraping", self.store_name)
            return 0

        published = 0
        for item in items[:MAX_PRODUCTS_PER_STORE]:
            try:
                message = PriceMessage(
                    scraper_id=self.scraper_id,
                    supermercado=self.store_name,
                    nombre_producto=item["nombre_producto"],
                    categoria=item.get("categoria", "general"),
                    precio=item["precio"],
                    precio_oferta=item.get("precio_oferta"),
                    url_producto=item["url_producto"],
                    timestamp=PriceMessage.now_iso(),
                )
                self.publisher.publish(message.model_dump())
                published += 1
            except Exception:  # un item malo no debe detener el resto
                logger.exception("[%s] No se pudo publicar item: %r", self.store_name, item)

        logger.info("[%s] Corrida finalizada: %s precios publicados", self.store_name, published)
        return published

    # ----------------------------------------------------------------- mock
    def _scrape_mock(self) -> list[dict]:
        """Genera precios sintéticos a partir del catálogo semilla.

        Aplica el factor por tienda, una variación aleatoria de ±6 % por
        corrida y ofertas ocasionales (~15 %), de modo que las comparativas
        y el historial tengan variabilidad realista.
        """
        items: list[dict] = []
        for nombre, categoria, base, _descr in CATALOG:
            variation = random.uniform(0.94, 1.06)
            precio = round(base * self.price_factor * variation)
            precio_oferta = None
            if random.random() < 0.15:  # ~15 % de los productos en oferta
                precio_oferta = round(precio * random.uniform(0.80, 0.93))

            slug = nombre.lower().replace(" ", "-").replace("ñ", "n")
            items.append({
                "nombre_producto": nombre,
                "categoria": categoria,
                "precio": float(precio),
                "precio_oferta": float(precio_oferta) if precio_oferta else None,
                "url_producto": f"{self.url_base}/p/{slug}",
            })
            time.sleep(SCRAPER_DELAY_SECONDS / 20)  # simula latencia leve
        return items

    # ----------------------------------------------------------------- real
    @abc.abstractmethod
    def _scrape_real(self) -> list[dict]:
        """Realiza el scraping real del sitio. Lo implementa cada cadena."""
        raise NotImplementedError

    # -------------------------------------------------------------- helpers
    def _get_soup(self, url: str) -> BeautifulSoup:
        """Descarga una página respetando el delay y devuelve su árbol HTML."""
        time.sleep(SCRAPER_DELAY_SECONDS)  # scraping responsable
        resp = self.session.get(url, timeout=SCRAPER_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    @staticmethod
    def _parse_clp(text: str) -> float | None:
        """Convierte un precio chileno ('$1.990') a float (1990.0)."""
        if not text:
            return None
        digits = "".join(ch for ch in text if ch.isdigit())
        return float(digits) if digits else None
