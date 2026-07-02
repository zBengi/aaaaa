"""Scraper de Unimarc (SMU)."""
from __future__ import annotations

import logging

from base_scraper import BaseScraper

logger = logging.getLogger("scraper.unimarc")

CATEGORY_URLS = [
    "https://www.unimarc.cl/category/lacteos",
    "https://www.unimarc.cl/category/despensa",
    "https://www.unimarc.cl/category/bebidas-y-licores",
    "https://www.unimarc.cl/category/cuidado-personal",
    "https://www.unimarc.cl/category/limpieza",
]


class UnimarcScraper(BaseScraper):
    store_name = "Unimarc"
    url_base = "https://www.unimarc.cl"
    price_factor = 1.02  # Unimarc en un punto intermedio

    def _scrape_real(self) -> list[dict]:
        items: list[dict] = []
        for url in CATEGORY_URLS:
            try:
                soup = self._get_soup(url)
            except Exception:
                logger.warning("[Unimarc] No se pudo descargar %s", url)
                continue

            for card in soup.select("div.product-card, article.product-item"):
                name_el = card.select_one(".product-card__name, .product-name, h3")
                price_el = card.select_one(".product-card__price, .price, span.value")
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
        logger.info("[Unimarc] Modo real extrajo %s productos", len(items))
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
