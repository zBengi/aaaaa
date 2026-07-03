"""
calibrar_matching.py – Herramienta de calibración del deduplicador.

Lee los productos REALES de la base de datos, calcula la similitud TF-IDF+coseno
entre todos los pares de la misma categoría y muestra:
  - Pares que se UNIRÍAN con el umbral actual (posibles duplicados a fusionar).
  - Pares en zona LÍMITE (para decidir si subir/bajar el umbral).
  - Un histograma de puntajes.

No modifica nada: solo analiza. Sirve para elegir UMBRAL_SIMILITUD sin adivinar.

Uso (dentro del contenedor del agregador):
    docker compose -p superprecios-s2 -f docker-compose.server2.yml \
        exec aggregator python calibrar_matching.py
"""

import os
from collections import defaultdict

from aggregator import (
    get_db_connection, normalizar_nombre, extraer_medidas,
    construir_idf, vectorizar, coseno, UMBRAL_SIMILITUD,
)


def analizar(rows, umbral=UMBRAL_SIMILITUD):
    """rows: lista de (id, nombre, categoria). Retorna (pares_ordenados, histograma)."""
    por_cat = defaultdict(list)
    for pid, nombre, categoria in rows:
        por_cat[categoria or "sin_categoria"].append((pid, nombre, normalizar_nombre(nombre)))

    pares = []
    hist = defaultdict(int)
    for categoria, items in por_cat.items():
        norms = [it[2] for it in items]
        index = construir_idf(norms)
        vecs = [vectorizar(n, index) for n in norms]
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                mi, mj = extraer_medidas(items[i][2]), extraer_medidas(items[j][2])
                if mi and mj and mi != mj:
                    continue  # el candado de medida los mantendría separados
                s = coseno(vecs[i], vecs[j])
                hist[round(s, 1)] += 1
                if s >= 0.40:  # solo reportamos pares con algo de parecido
                    pares.append((s, categoria, items[i], items[j]))
    pares.sort(reverse=True, key=lambda x: x[0])
    return pares, hist


def main():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, categoria FROM productos ORDER BY categoria, nombre")
            rows = cur.fetchall()
    finally:
        conn.close()

    print(f"Productos en la base: {len(rows)}")
    print(f"Umbral actual (UMBRAL_SIMILITUD): {UMBRAL_SIMILITUD}\n")

    pares, hist = analizar(rows)

    unirian   = [p for p in pares if p[0] >= UMBRAL_SIMILITUD]
    limite    = [p for p in pares if UMBRAL_SIMILITUD - 0.15 <= p[0] < UMBRAL_SIMILITUD]

    print(f"===== SE UNIRÍAN con umbral {UMBRAL_SIMILITUD} ({len(unirian)} pares) =====")
    print("(idealmente son el mismo producto en distintas tiendas)")
    for s, cat, a, b in unirian[:40]:
        print(f"  {s:4.2f} [{cat}]  #{a[0]} {a[1][:36]:36} <-> #{b[0]} {b[1][:36]}")

    print(f"\n===== ZONA LÍMITE (justo debajo del umbral) ({len(limite)} pares) =====")
    print("(revisa si alguno DEBERÍA unirse -> baja el umbral; o NO -> déjalo)")
    for s, cat, a, b in limite[:40]:
        print(f"  {s:4.2f} [{cat}]  #{a[0]} {a[1][:36]:36} <-> #{b[0]} {b[1][:36]}")

    print("\n===== HISTOGRAMA de puntajes (pares con parecido) =====")
    for k in sorted(hist):
        print(f"  {k:0.1f} | {'#' * min(hist[k], 60)} ({hist[k]})")


if __name__ == "__main__":
    main()