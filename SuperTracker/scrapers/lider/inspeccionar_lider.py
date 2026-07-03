"""
inspeccionar_lider.py – DIAGNÓSTICO de super.lider.cl.

super.lider.cl ya no usa __NEXT_DATA__. Este script no intenta scrapear:
solo reporta CÓMO viene embebida la data en el HTML, para poder escribir el
parser correcto. Pega su salida (es corta) y con eso ajusto el scraper.

Uso (dentro del contenedor del scraper de Líder):
    docker cp scrapers/lider/inspeccionar_lider.py scraper_lider:/app/inspeccionar_lider.py
    docker compose -p superprecios-s1 -f docker-compose.server1.yml \
        exec scraper_lider python inspeccionar_lider.py
"""

import re
import json
import requests

from scraper_base import HEADERS

BASE_URL = "https://super.lider.cl/search"


def diagnosticar(termino: str):
    print("=" * 68)
    print(f"BÚSQUEDA: {termino!r}")
    print("=" * 68)
    try:
        resp = requests.get(
            BASE_URL,
            params={"q": termino, "page": 1},
            headers={**HEADERS,
                     "Accept": "text/html,application/xhtml+xml",
                     "Referer": "https://super.lider.cl/"},
            timeout=20,
        )
    except Exception as exc:
        print(f"  ERROR de red: {exc}\n")
        return
    html = resp.text
    print(f"HTTP {resp.status_code} | {len(html):,} bytes")

    # 1) ¿qué mecanismo de Next.js usa?
    print("\n[1] Mecanismo de embebido:")
    print(f"    __NEXT_DATA__ : {'__NEXT_DATA__' in html}")
    print(f"    __next_f (App Router streaming) : {'__next_f' in html}")
    print(f"    comillas escapadas \\\"  : {html.count(chr(92)+chr(34))} (mucho = data en chunks RSC)")

    # 2) ¿aparecen los campos de producto? (contamos la forma cruda, con o sin escape)
    print("\n[2] Campos de producto encontrados (conteo bruto):")
    for token in ["/ip/", "canonicalUrl", "priceInfo", "currentPrice",
                  "linePrice", "\"name\"", "name\\\":", "brand", "usItemId"]:
        print(f"    {token:16} : {html.count(token)}")

    # 3) contexto alrededor del primer indicio de precio/producto
    print("\n[3] Contexto del primer 'priceInfo' o 'canonicalUrl' (crudo, ~500 chars):")
    for marker in ("priceInfo", "canonicalUrl", "currentPrice"):
        i = html.find(marker)
        if i != -1:
            snippet = html[max(0, i - 120): i + 380]
            snippet = " ".join(snippet.split())   # colapsar espacios/saltos
            print(f"    (marcador: {marker})")
            print("    " + snippet[:500])
            break
    else:
        print("    No se hallaron marcadores de precio conocidos.")

    # 4) contexto de un enlace de producto (por si hay que parsear el HTML directo)
    print("\n[4] Contexto de un enlace /ip/ (para parseo por HTML si hiciera falta):")
    m = re.search(r'.{80}/ip/[^"\\ ]{5,60}.{120}', html)
    print("    " + (" ".join(m.group(0).split())[:400] if m else "sin enlaces /ip/"))
    print()


if __name__ == "__main__":
    for termino in ("colun", "leche"):
        diagnosticar(termino)