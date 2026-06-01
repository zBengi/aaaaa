"""
scraper_unimarc.py – Scraper para Unimarc Chile.

Extrae productos de las categorías prioritarias: alimentos,
higiene personal y limpieza del hogar.

NOTA: Los selectores CSS están definidos como constantes al inicio
del archivo para facilitar su actualización si el sitio cambia
su estructura HTML.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper_base import ScraperBase, PrecioMessage

# ── Selectores CSS (actualizar si cambia la estructura del sitio) ─
SEL_PRODUCTO_CARD = "article.product-card"
SEL_NOMBRE        = "h3.product-card__title"
SEL_PRECIO        = "span.price__current"
SEL_CODIGO_BARRA  = "div[data-barcode]"

# ── URLs por categoría prioritaria ────────────────────────────────
CATEGORIAS = {
    "alimentos": "https://www.unimarc.cl/alimentos",
    "higiene":   "https://www.unimarc.cl/higiene-personal",
    "limpieza":  "https://www.unimarc.cl/limpieza-del-hogar",
}

MAX_PAGINAS_POR_CATEGORIA = 5


class ScraperUnimarc(ScraperBase):

    def __init__(self):
        super().__init__("unimarc")

    def scrape(self) -> list[PrecioMessage]:
        mensajes: list[PrecioMessage] = []

        for categoria, url_base in CATEGORIAS.items():
            self.logger.info("Scrapeando categoría '%s' en Unimarc…", categoria)

            for pagina in range(1, MAX_PAGINAS_POR_CATEGORIA + 1):
                url = f"{url_base}?page={pagina}"
                soup = self.get_page(url)
                if soup is None:
                    break

                cards = soup.select(SEL_PRODUCTO_CARD)
                if not cards:
                    self.logger.debug(
                        "Sin productos en página %d de '%s'; fin de categoría.",
                        pagina, categoria,
                    )
                    break

                for card in cards:
                    msg = self._parse_card(card, categoria, url)
                    if msg:
                        mensajes.append(msg)

        self.logger.info("Unimarc: %d productos extraídos.", len(mensajes))
        return mensajes

    def _parse_card(
        self,
        card,
        categoria: str,
        url_pagina: str,
    ) -> PrecioMessage | None:
        try:
            nombre_tag = card.select_one(SEL_NOMBRE)
            precio_tag = card.select_one(SEL_PRECIO)

            if not nombre_tag or not precio_tag:
                return None

            nombre = nombre_tag.get_text(strip=True)
            precio_raw = precio_tag.get_text(strip=True)
            precio = self._parse_precio(precio_raw)
            if precio is None:
                return None

            bc_tag = card.select_one(SEL_CODIGO_BARRA)
            codigo_barra = bc_tag["data-barcode"] if bc_tag else None

            url_producto = url_pagina
            enlace = card.find("a", href=True)
            if enlace:
                href = enlace["href"]
                url_producto = (
                    href if href.startswith("http")
                    else f"https://www.unimarc.cl{href}"
                )

            return PrecioMessage(
                supermercado="Unimarc",
                nombre_producto=nombre,
                categoria=categoria,
                codigo_barra=codigo_barra,
                precio=precio,
                url_producto=url_producto,
            )
        except Exception as exc:
            self.logger.warning("Error parseando card de Unimarc: %s", exc)
            return None

    @staticmethod
    def _parse_precio(texto: str) -> float | None:
        """Convierte '$1.299' → 1299.0"""
        try:
            limpio = texto.replace("$", "").replace(".", "").replace(",", ".").strip()
            return float(limpio)
        except ValueError:
            return None


if __name__ == "__main__":
    ScraperUnimarc().start_scheduler()
