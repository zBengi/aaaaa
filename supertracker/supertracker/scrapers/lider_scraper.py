"""Scraper de Líder (Walmart Chile)."""
from __future__ import annotations

import logging

from base_scraper import BaseScraper

logger = logging.getLogger("scraper.lider")

CATEGORY_URLS = [
    "https://www.lider.cl/supermercado/category/Lacteos",
    "https://www.lider.cl/supermercado/category/Despensa",
    "https://www.lider.cl/supermercado/category/Bebidas-y-Licores",
    "https://www.lider.cl/supermercado/category/Cuidado-Personal",
    "https://www.lider.cl/supermercado/category/Limpieza",
]


class LiderScraper(BaseScraper):
    store_name = "Líder"
    url_base = "https://www.lider.cl"
    price_factor = 0.97  # Líder suele ser más competitivo en precio

    def _scrape_real(self) -> list[dict]:
        items: list[dict] = []
        for url in CATEGORY_URLS:
            try:
                soup = self._get_soup(url)
            except Exception:
                logger.warning("[Líder] No se pudo descargar %s", url)
                continue

            for card in soup.select("div.product-tile, article[data-product-id]"):
                name_el = card.select_one(".product-name, .tile-name, a.link")
                price_el = card.select_one(".price, .sales .value, span.product-price")
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
        logger.info("[Líder] Modo real extrajo %s productos", len(items))
        return items

    @staticmethod
    def _categoria_desde_url(url: str) -> str:
        u = url.lower()
        if "lacteos" in u:
            return "lácteo"
        if "bebidas" in u:
            return "bebida"
        if "personal" in u:
            return "higiene"
        if "limpieza" in u:
            return "limpieza"
        return "alimento"
