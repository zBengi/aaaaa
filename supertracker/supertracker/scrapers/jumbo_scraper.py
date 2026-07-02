"""Scraper de Jumbo (Cencosud)."""
from __future__ import annotations

import logging

from base_scraper import BaseScraper

logger = logging.getLogger("scraper.jumbo")

# Páginas de listado por categoría usadas en modo real.
CATEGORY_URLS = [
    "https://www.jumbo.cl/lacteos",
    "https://www.jumbo.cl/despensa",
    "https://www.jumbo.cl/bebidas-y-licores",
    "https://www.jumbo.cl/cuidado-personal",
    "https://www.jumbo.cl/limpieza",
]


class JumboScraper(BaseScraper):
    store_name = "Jumbo"
    url_base = "https://www.jumbo.cl"
    price_factor = 1.08  # Jumbo suele ser algo más caro

    def _scrape_real(self) -> list[dict]:
        items: list[dict] = []
        for url in CATEGORY_URLS:
            try:
                soup = self._get_soup(url)
            except Exception:
                logger.warning("[Jumbo] No se pudo descargar %s", url)
                continue

            # Selectores del catálogo de Jumbo (VTEX). Pueden variar; se usan
            # selectores flexibles y la corrida tolera cambios devolviendo [].
            for card in soup.select("article.product, div.shelf-product"):
                name_el = card.select_one(".product-name, .shelf-product-name")
                price_el = card.select_one(".price, .product-price, span.best-price")
                link_el = card.select_one("a[href]")
                if not (name_el and price_el):
                    continue
                precio = self._parse_clp(price_el.get_text(strip=True))
                if precio is None:
                    continue
                href = link_el["href"] if link_el else url
                items.append({
                    "nombre_producto": name_el.get_text(strip=True),
                    "categoria": self._categoria_desde_url(url),
                    "precio": precio,
                    "precio_oferta": None,
                    "url_producto": href if href.startswith("http") else f"{self.url_base}{href}",
                })
        logger.info("[Jumbo] Modo real extrajo %s productos", len(items))
        return items

    @staticmethod
    def _categoria_desde_url(url: str) -> str:
        if "lacteos" in url:
            return "lácteo"
        if "bebidas" in url:
            return "bebida"
        if "personal" in url:
            return "higiene"
        if "limpieza" in url:
            return "limpieza"
        return "alimento"
