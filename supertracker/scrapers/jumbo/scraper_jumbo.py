"""
scraper_jumbo.py – Scraper para Jumbo Chile (API Constructor.io).

"""

import sys, os, uuid, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper_base import ScraperBase, PrecioMessage

API_BASE = "https://pwcdauseo-zone.cnstrc.com/search"
API_KEY  = "key_JopvNXKS61kwGkBe"

# Headers específicos de Jumbo → Constructor (CROSS-SITE).
HEADERS_JUMBO = {
    "Origin":         "https://www.jumbo.cl",
    "Referer":        "https://www.jumbo.cl/",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",   # ← el fix clave: cnstrc.com ≠ jumbo.cl
}

# Términos de búsqueda reales por categoría
CATEGORIAS = {
    "alimentos": ["leche", "yogur", "mantequilla", "queso", "huevos"],
    "higiene":   ["shampoo", "jabon", "pasta dental", "desodorante"],
    "limpieza":  ["detergente", "cloro", "limpiapisos", "esponja"],
}

RESULTADOS_POR_PAGINA = 30
MAX_PAGINAS           = 5


class ScraperJumbo(ScraperBase):

    def __init__(self):
        super().__init__("jumbo")
        self._client_id  = str(uuid.uuid4())
        self._session_id = 1

    def scrape(self) -> list[PrecioMessage]:
        mensajes = []
        for categoria, terminos in CATEGORIAS.items():
            for termino in terminos:
                self.logger.info("Jumbo: buscando '%s' (%s)…", termino, categoria)
                mensajes.extend(self._scrape_termino(categoria, termino))
        self.logger.info("Jumbo: %d productos extraídos.", len(mensajes))
        return mensajes

    def _scrape_termino(self, categoria: str, termino: str) -> list[PrecioMessage]:
        mensajes = []
        for pagina in range(1, MAX_PAGINAS + 1):
            params = {
                "key":                  API_KEY,
                "c":                    "ciojs-2.1418.5",
                "i":                    self._client_id,
                "s":                    self._session_id,
                "section":              "Products",
                "page":                 pagina,
                "num_results_per_page": RESULTADOS_POR_PAGINA,
                "_dt":                  int(time.time() * 1000),   # ← timestamp que envía ciojs
                "origin_referrer":      "https://www.jumbo.cl/busqueda",
                "fmt_options[groups_start]":     "current",
                "fmt_options[groups_max_depth]": "1",
            }
            data = self.get_json_params_headers(
                f"{API_BASE}/{termino}", params, HEADERS_JUMBO
            )
            if not data:
                break

            items = data.get("response", {}).get("results", [])
            if not items:
                break

            for item in items:
                msg = self._parse_item(item, categoria)
                if msg:
                    mensajes.append(msg)

            total = data.get("response", {}).get("total_num_results", 0)
            if pagina * RESULTADOS_POR_PAGINA >= total:
                break

        return mensajes

    def _parse_item(self, item: dict, categoria: str) -> PrecioMessage | None:
        try:
            d = item.get("data", {})

            nombre = d.get("ProductName") or d.get("value") or item.get("value", "")
            nombre = nombre.strip()
            if not nombre:
                return None

            # Usar sellingPrice (precio con descuento) o price
            precio = d.get("sellingPrice") or d.get("price")
            if not precio or float(precio) <= 0:
                return None

            # Sin código de barra en esta API, usar RefId como referencia
            codigo_barra = d.get("RefId") or None

            url_producto = d.get("url", "")
            if url_producto and not url_producto.startswith("http"):
                url_producto = f"https://www.jumbo.cl{url_producto}"
            if not url_producto:
                url_producto = "https://www.jumbo.cl"

            return PrecioMessage(
                supermercado="Jumbo",
                nombre_producto=nombre,
                categoria=categoria,
                codigo_barra=str(codigo_barra) if codigo_barra else None,
                precio=float(precio),
                url_producto=url_producto,
            )
        except Exception as exc:
            self.logger.warning("Error parseando item Jumbo: %s", exc)
            return None


if __name__ == "__main__":
    ScraperJumbo().start_scheduler()