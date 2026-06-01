"""
scraper_lider.py – Scraper para Líder Chile.
Líder usa SSR (Next.js) — los productos están en el tag __NEXT_DATA__ del HTML.
Se parsea el HTML para extraer el JSON embebido.
"""

import sys, os, re, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper_base import ScraperBase, PrecioMessage
import requests
from scraper_base import HEADERS

BASE_URL = "https://www.lider.cl/search"

CATEGORIAS = {
    "alimentos": ["leche", "yogur", "mantequilla", "queso", "huevos"],
    "higiene":   ["shampoo", "jabon", "pasta dental", "desodorante"],
    "limpieza":  ["detergente", "cloro", "limpiapisos", "esponja"],
}

MAX_PAGINAS = 5


class ScraperLider(ScraperBase):

    def __init__(self):
        super().__init__("lider")

    def scrape(self) -> list[PrecioMessage]:
        mensajes = []
        for categoria, terminos in CATEGORIAS.items():
            for termino in terminos:
                self.logger.info("Líder: buscando '%s' (%s)…", termino, categoria)
                mensajes.extend(self._scrape_termino(categoria, termino))
        self.logger.info("Líder: %d productos extraídos.", len(mensajes))
        return mensajes

    def _scrape_termino(self, categoria: str, termino: str) -> list[PrecioMessage]:
        mensajes = []
        for pagina in range(1, MAX_PAGINAS + 1):
            import time, random
            time.sleep(random.uniform(1, 3))
            try:
                resp = requests.get(
                    BASE_URL,
                    params={"q": termino, "page": pagina},
                    headers={
                        **HEADERS,
                        "Accept": "text/html,application/xhtml+xml",
                        "Referer": "https://www.lider.cl",
                    },
                    timeout=20,
                )
                resp.raise_for_status()
            except Exception as exc:
                self.logger.error("Error HTTP Líder '%s' p%d: %s", termino, pagina, exc)
                break

            # Extraer __NEXT_DATA__ del HTML
            match = re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                resp.text, re.DOTALL
            )
            if not match:
                self.logger.warning("Sin __NEXT_DATA__ en página %d de '%s'", pagina, termino)
                break

            try:
                next_data = json.loads(match.group(1))
            except json.JSONDecodeError as exc:
                self.logger.error("Error parseando __NEXT_DATA__: %s", exc)
                break

            items = self._extract_items(next_data)
            if not items:
                self.logger.debug("Sin productos en página %d de '%s'", pagina, termino)
                break

            for item in items:
                msg = self._parse_item(item, categoria)
                if msg:
                    mensajes.append(msg)

            # Líder muestra 40 por página; si hay menos, es la última
            if len(items) < 40:
                break

        return mensajes

    def _extract_items(self, next_data: dict) -> list:
        """Navega el árbol de Next.js para encontrar la lista de productos."""
        try:
            props = next_data.get("props", {})
            page_props = props.get("pageProps", {})

            # Ruta principal: initialData o searchData
            for key in ("initialData", "searchData", "data"):
                data = page_props.get(key, {})
                if data:
                    # Intentar varias subestructuras conocidas
                    items = (
                        data.get("items")
                        or data.get("products", {}).get("items")
                        or data.get("searchResult", {}).get("itemStacks", [{}])[0].get("items")
                        or []
                    )
                    if items:
                        return items

            # Ruta alternativa: itemStacks directo en pageProps
            stacks = page_props.get("itemStacks", [])
            if stacks:
                return stacks[0].get("items", [])

        except Exception as exc:
            self.logger.warning("Error navegando __NEXT_DATA__: %s", exc)

        return []

    def _parse_item(self, item: dict, categoria: str) -> PrecioMessage | None:
        try:
            nombre = item.get("name", "").strip()
            if not nombre:
                return None

            # Precio: puede venir en priceInfo, price o como número directo
            price_info = item.get("priceInfo", {}) or {}
            precio = (
                price_info.get("price")
                or price_info.get("currentPrice")
                or price_info.get("priceDisplay")
                or item.get("price")
                or item.get("currentPrice")
            )

            # A veces viene como string "$1.290"
            if isinstance(precio, str):
                precio = self._limpiar_precio(precio)
            
            if not precio or float(precio) <= 0:
                return None

            codigo_barra = (
                item.get("upc")
                or item.get("ean")
                or item.get("itemId")
                or None
            )

            url_producto = item.get("canonicalUrl") or item.get("url") or ""
            if url_producto and not url_producto.startswith("http"):
                url_producto = f"https://www.lider.cl{url_producto}"
            if not url_producto:
                url_producto = "https://www.lider.cl"

            return PrecioMessage(
                supermercado="Lider",
                nombre_producto=nombre,
                categoria=categoria,
                codigo_barra=str(codigo_barra) if codigo_barra else None,
                precio=float(precio),
                url_producto=url_producto,
            )
        except Exception as exc:
            self.logger.warning("Error parseando item Líder: %s", exc)
            return None

    @staticmethod
    def _limpiar_precio(texto: str) -> float | None:
        try:
            return float(texto.replace("$", "").replace(".", "").replace(",", ".").strip())
        except (ValueError, AttributeError):
            return None


if __name__ == "__main__":
    ScraperLider().start_scheduler()