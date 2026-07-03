"""
scraper_lider.py – Scraper para Líder Chile.
Líder usa SSR (Next.js) — los productos están en el tag __NEXT_DATA__ del HTML.
Se parsea el HTML para extraer el JSON embebido.
"""

import sys, os, re, json, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from scraper_base import ScraperBase, PrecioMessage, HEADERS

BASE_URL = "https://super.lider.cl/search"

CATEGORIAS = {
    "alimentos": ["leche", "yogur", "mantequilla", "queso", "huevos"],
    "higiene":   ["shampoo", "jabon", "pasta dental", "desodorante"],
    "limpieza":  ["detergente", "cloro", "limpiapisos", "esponja"],
}

MAX_PAGINAS = 5
POR_PAGINA_ESPERADO = 40   # Walmart Glass muestra ~40 por página


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
            time.sleep(random.uniform(1, 3))
            try:
                resp = requests.get(
                    BASE_URL,
                    params={"q": termino, "page": pagina},
                    headers={
                        **HEADERS,
                        "Accept": "text/html,application/xhtml+xml",
                        "Referer": "https://super.lider.cl/",
                    },
                    timeout=20,
                )
                resp.raise_for_status()
            except Exception as exc:
                self.logger.error("Error HTTP Líder '%s' p%d: %s", termino, pagina, exc)
                break

            next_data = self._extraer_next_data(resp.text)
            if next_data is None:
                self.logger.warning("Sin __NEXT_DATA__ en '%s' p%d", termino, pagina)
                break

            items = self._encontrar_productos(next_data)
            if not items:
                self.logger.debug("Sin productos en '%s' p%d", termino, pagina)
                break

            for item in items:
                msg = self._parse_item(item, categoria)
                if msg:
                    mensajes.append(msg)

            if len(items) < POR_PAGINA_ESPERADO:
                break   # última página

        return mensajes

    # ── Extracción del JSON embebido ──────────────────────────────

    @staticmethod
    def _extraer_next_data(html: str):
        match = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            html, re.DOTALL,
        )
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _encontrar_productos(next_data: dict) -> list:
        """
        Recorre TODO el árbol de __NEXT_DATA__ y devuelve la lista más larga de
        objetos que parezcan productos (tienen 'name' + algún campo de precio).
        Robusto a que Walmart cambie la ruta interna del JSON.
        """
        mejor: list = []

        def es_producto(d) -> bool:
            return (isinstance(d, dict)
                    and isinstance(d.get("name"), str)
                    and any(k in d for k in ("priceInfo", "price", "priceRange")))

        def walk(x):
            nonlocal mejor
            if isinstance(x, list):
                productos = [e for e in x if es_producto(e)]
                if len(productos) > len(mejor):
                    mejor = productos
                for e in x:
                    walk(e)
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)

        walk(next_data)
        return mejor

    # ── Parseo de un producto ─────────────────────────────────────

    def _parse_item(self, item: dict, categoria: str) -> PrecioMessage | None:
        try:
            nombre = (item.get("name") or "").strip()
            if not nombre:
                return None

            # En super.lider.cl la marca viene en un campo aparte y a veces NO
            # está en el nombre. Se añade al nombre (si falta) para que el producto
            # coincida con las otras tiendas, que sí incluyen la marca.
            marca = self._extraer_marca(item)
            if marca and marca.lower() not in nombre.lower():
                nombre = f"{nombre} {marca}"

            precio = self._extraer_precio(item)
            if not precio or precio <= 0:
                return None

            codigo_barra = (
                item.get("upc") or item.get("ean")
                or item.get("usItemId") or item.get("id") or None
            )

            url = item.get("canonicalUrl") or item.get("url") or ""
            if url and not url.startswith("http"):
                url = f"https://super.lider.cl{url}"
            if not url:
                url = "https://super.lider.cl"

            return PrecioMessage(
                supermercado="Lider",
                nombre_producto=nombre,
                categoria=categoria,
                codigo_barra=str(codigo_barra) if codigo_barra else None,
                precio=float(precio),
                url_producto=url,
            )
        except Exception as exc:
            self.logger.warning("Error parseando item Líder: %s", exc)
            return None

    @staticmethod
    def _extraer_marca(item: dict) -> str:
        """La marca puede venir como string o dentro de un objeto."""
        b = item.get("brand") or item.get("brandName") or item.get("brandInfo")
        if isinstance(b, dict):
            b = b.get("name") or b.get("brandName") or ""
        return b.strip() if isinstance(b, str) else ""

    @classmethod
    def _extraer_precio(cls, item: dict) -> float | None:
        """Extrae el precio actual manejando la estructura de Walmart Glass."""
        pi = item.get("priceInfo") or {}
        cp = pi.get("currentPrice") or {}
        candidatos = [
            cp.get("price") if isinstance(cp, dict) else None,          # numérico
            cp.get("priceString") if isinstance(cp, dict) else None,    # "$2.150"
            pi.get("linePrice"),
            pi.get("currentPrice") if not isinstance(pi.get("currentPrice"), dict) else None,
            item.get("price"),
            item.get("currentPrice"),
        ]
        for c in candidatos:
            p = cls._a_numero(c)
            if p:
                return p
        return None

    @classmethod
    def _a_numero(cls, v) -> float | None:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v) if v > 0 else None
        if isinstance(v, str):
            return cls._limpiar_precio(v)
        return None

    @staticmethod
    def _limpiar_precio(texto: str) -> float | None:
        # "$2.150" -> 2150 ; "1.290" -> 1290 (punto = separador de miles en CL)
        m = re.search(r"[\d\.\,]+", texto)
        if not m:
            return None
        limpio = m.group(0).replace(".", "").replace(",", ".")
        try:
            val = float(limpio)
            return val if val > 0 else None
        except ValueError:
            return None


if __name__ == "__main__":
    ScraperLider().start_scheduler()