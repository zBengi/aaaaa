"""
scraper_unimarc.py – Scraper para Unimarc Chile.
API: GET bff-unimarc-ecommerce.unimarc.cl/catalog/product/search
Estructura: { availableProducts: [{ price: { price: "$1.250" }, item: { name, ean, slug } }] }
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper_base import ScraperBase, PrecioMessage

API_URL = "https://bff-unimarc-ecommerce.unimarc.cl/catalog/product/search"

HEADERS_UNIMARC = {
    "Origin":         "https://www.unimarc.cl",
    "Referer":        "https://www.unimarc.cl/search?q=leche",
    "sec-fetch-site": "same-site",
}

CATEGORIAS = {
    "alimentos": ["leche", "yogur", "mantequilla", "queso", "huevos"],
    "higiene":   ["shampoo", "jabon", "pasta dental", "desodorante"],
    "limpieza":  ["detergente", "cloro", "limpiapisos", "esponja"],
}

RESULTADOS_POR_PAGINA = 30
MAX_PAGINAS           = 5


class ScraperUnimarc(ScraperBase):

    def __init__(self):
        super().__init__("unimarc")

    def scrape(self) -> list[PrecioMessage]:
        mensajes = []
        for categoria, terminos in CATEGORIAS.items():
            for termino in terminos:
                self.logger.info("Unimarc: buscando '%s' (%s)…", termino, categoria)
                mensajes.extend(self._scrape_termino(categoria, termino))
        self.logger.info("Unimarc: %d productos extraídos.", len(mensajes))
        return mensajes

    def _scrape_termino(self, categoria: str, termino: str) -> list[PrecioMessage]:
        mensajes = []
        for pagina in range(1, MAX_PAGINAS + 1):
            params = {
                "query": termino,
                "page":  pagina,
                "count": RESULTADOS_POR_PAGINA,
            }
            data = self.get_json_params_headers(API_URL, params, HEADERS_UNIMARC)
            if not data:
                break

            items = data.get("availableProducts", [])
            if not items:
                break

            for producto in items:
                msg = self._parse_producto(producto, categoria)
                if msg:
                    mensajes.append(msg)

            if len(items) < RESULTADOS_POR_PAGINA:
                break

        return mensajes

    def _parse_producto(self, producto: dict, categoria: str) -> PrecioMessage | None:
        try:
            item  = producto.get("item", {})
            price = producto.get("price", {})

            nombre = item.get("name", "").strip()
            if not nombre:
                return None

            # Precio viene como "$1.250" → limpiar a float
            precio_str = price.get("price", "")
            precio = self._parse_precio(precio_str)
            if precio is None or precio <= 0:
                return None

            codigo_barra = item.get("ean") or None
            slug = item.get("slug", "")
            url_producto = (
                f"https://www.unimarc.cl{slug}" if slug
                else "https://www.unimarc.cl"
            )

            return PrecioMessage(
                supermercado="Unimarc",
                nombre_producto=nombre,
                categoria=categoria,
                codigo_barra=str(codigo_barra) if codigo_barra else None,
                precio=precio,
                url_producto=url_producto,
            )
        except Exception as exc:
            self.logger.warning("Error parseando producto Unimarc: %s", exc)
            return None

    @staticmethod
    def _parse_precio(texto: str) -> float | None:
        """Convierte '$1.250' → 1250.0"""
        try:
            limpio = texto.replace("$", "").replace(".", "").replace(",", ".").strip()
            return float(limpio)
        except (ValueError, AttributeError):
            return None


if __name__ == "__main__":
    ScraperUnimarc().start_scheduler()