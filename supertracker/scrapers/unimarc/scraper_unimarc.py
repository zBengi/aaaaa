"""
scraper_unimarc.py – Scraper para Unimarc Chile (BFF).

API: POST https://bff-unimarc-ecommerce.unimarc.cl/catalog/product/search
Body real (capturado):
    {"from":"0","orderBy":"","searching":"leche",
     "promotionsOnly":false,"to":"49","userTriggered":true}
Respuesta: { availableProducts: [{ price: { price: "$1.250" }, item: { name, ean, slug } }] }

"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper_base import ScraperBase, PrecioMessage

API_URL = "https://bff-unimarc-ecommerce.unimarc.cl/catalog/product/search"

# Headers estáticos del BFF de Unimarc (capturados del Network tab).
# 'anonymous' y 'session' son tokens de sesión; descoméntalos y pega los
# reales solo si el BFF empieza a rechazar las peticiones (cuerpo en el log).
HEADERS_UNIMARC = {
    "Origin":         "https://www.unimarc.cl",
    "Referer":        "https://www.unimarc.cl/",
    "channel":        "UNIMARC",
    "source":         "web",
    "version":        "1.0.0",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    # "anonymous": "yjaGcr3EJVGZoOxZtCNaP",
    # "session":   "RFi4hAXEHQWMvmuk-p1jh",
}

CATEGORIAS = {
    "alimentos": ["leche", "yogur", "mantequilla", "queso", "huevos"],
    "higiene":   ["shampoo", "jabon", "pasta dental", "desodorante"],
    "limpieza":  ["detergente", "cloro", "limpiapisos", "esponja"],
}

PAGE_SIZE    = 50   # la API devuelve 50 por ventana (from=0, to=49)
MAX_VENTANAS = 5    # hasta 250 resultados por término


class ScraperUnimarc(ScraperBase):

    def __init__(self):
        super().__init__("unimarc")

    def _build_payload(self, termino: str, desde: int, hasta: int) -> dict:
        """Cuerpo exacto del POST. 'from'/'to' van como strings."""
        return {
            "from":           str(desde),
            "orderBy":        "",
            "searching":      termino,
            "promotionsOnly": False,
            "to":             str(hasta),
            "userTriggered":  True,
        }

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
        for ventana in range(MAX_VENTANAS):
            desde = ventana * PAGE_SIZE
            hasta = desde + PAGE_SIZE - 1   # 0–49, 50–99, …
            payload = self._build_payload(termino, desde, hasta)

            data = self.post_json(API_URL, payload, extra_headers=HEADERS_UNIMARC)
            if not data:
                break

            items = data.get("availableProducts", [])
            if not items:
                break

            for producto in items:
                msg = self._parse_producto(producto, categoria)
                if msg:
                    mensajes.append(msg)

            # Si vino menos de una ventana completa, era la última página.
            if len(items) < PAGE_SIZE:
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