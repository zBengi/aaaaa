"""Catálogo semilla de productos chilenos para el modo ``mock``.

Permite un demo reproducible de extremo a extremo (scraper → RabbitMQ →
agregador → PostgreSQL → API → frontend) sin depender de la estructura HTML
de los sitios reales, que son SPAs con protección anti-bot y selectores
cambiantes. Cada producto tiene un precio base de referencia; el scraper mock
le aplica una variación por tienda y por corrida para simular fluctuaciones
reales y ofertas ocasionales.

Categorías prioritarias del diseño: alimentos, higiene personal y limpieza.
"""
from __future__ import annotations

# (nombre, categoria, precio_base_CLP, descripcion)
CATALOG: list[tuple[str, str, int, str]] = [
    # --- Alimentos ---------------------------------------------------------
    ("Leche Entera Soprole 1L",            "lácteo",   1190, "Leche entera larga vida en caja de 1 litro"),
    ("Leche Descremada Colun 1L",          "lácteo",   1150, "Leche descremada larga vida 1 litro"),
    ("Yogurt Natural Soprole 150g",        "lácteo",    490, "Yogurt natural pote individual 150 gramos"),
    ("Mantequilla Soprole 250g",           "lácteo",   2790, "Mantequilla con sal pan de 250 gramos"),
    ("Queso Gauda Laminado 250g",          "lácteo",   3490, "Queso gauda laminado bandeja 250 gramos"),
    ("Huevos Blancos 12 unidades",         "alimento", 2990, "Cartón de docena de huevos blancos"),
    ("Pan de Molde Ideal Blanco 500g",     "alimento", 1990, "Pan de molde blanco bolsa 500 gramos"),
    ("Arroz Grado 1 Tucapel 1kg",          "alimento", 1490, "Arroz grado 1 bolsa de 1 kilo"),
    ("Fideos Spaghetti Carozzi 400g",      "alimento", 1090, "Fideos spaghetti N°5 bolsa 400 gramos"),
    ("Aceite Vegetal Chef 900ml",          "alimento", 2290, "Aceite vegetal botella 900 ml"),
    ("Azúcar Iansa 1kg",                   "alimento", 1290, "Azúcar granulada bolsa de 1 kilo"),
    ("Sal de Mesa Lobos 1kg",              "alimento",  890, "Sal de mesa fina bolsa de 1 kilo"),
    ("Harina Sin Polvos Selecta 1kg",      "alimento", 1190, "Harina de trigo sin polvos de hornear 1 kilo"),
    ("Atún Lomito San José 170g",          "alimento", 1690, "Atún lomitos en aceite lata 170 gramos"),
    ("Café Instantáneo Nescafé 170g",      "alimento", 5990, "Café instantáneo frasco 170 gramos"),
    ("Té Negro Supremo 20 bolsas",         "alimento", 1390, "Té negro caja con 20 bolsitas"),
    ("Mermelada Frutilla Watt's 250g",     "alimento", 1790, "Mermelada de frutilla frasco 250 gramos"),
    ("Galletas Soda McKay 6 paquetes",     "alimento", 2190, "Galletas de soda pack familiar 6 unidades"),
    ("Bebida Coca-Cola 1.5L",              "bebida",   1990, "Bebida gaseosa botella 1.5 litros"),
    ("Bebida Sprite 1.5L",                 "bebida",   1890, "Bebida gaseosa lima limón 1.5 litros"),
    ("Jugo Watt's Naranja 1L",             "bebida",   1290, "Néctar de naranja caja 1 litro"),
    ("Agua Mineral Vital Sin Gas 1.6L",    "bebida",    990, "Agua mineral sin gas botella 1.6 litros"),
    ("Cerveza Cristal Lata 470ml",         "bebida",   1290, "Cerveza lager lata 470 ml"),
    # --- Higiene personal --------------------------------------------------
    ("Shampoo Sedal 340ml",                "higiene",  3490, "Shampoo para todo tipo de cabello 340 ml"),
    ("Jabón Lux Barra 125g",               "higiene",   790, "Jabón de tocador en barra 125 gramos"),
    ("Pasta Dental Colgate 90g",           "higiene",  1690, "Pasta dental anticaries tubo 90 gramos"),
    ("Desodorante Rexona Aerosol 150ml",   "higiene",  2990, "Desodorante antitranspirante aerosol 150 ml"),
    ("Papel Higiénico Confort 12 rollos",  "higiene",  6990, "Papel higiénico doble hoja pack 12 rollos"),
    ("Toallas Húmedas Babysec 80un",       "higiene",  2490, "Toallitas húmedas paquete 80 unidades"),
    ("Cepillo de Dientes Oral-B",          "higiene",  1990, "Cepillo dental cerdas medianas"),
    # --- Limpieza del hogar ------------------------------------------------
    ("Detergente Líquido Omo 3L",          "limpieza", 8990, "Detergente líquido para ropa 3 litros"),
    ("Lavalozas Quix 750ml",               "limpieza", 1990, "Lavalozas concentrado limón 750 ml"),
    ("Cloro Clorox 900ml",                 "limpieza", 1290, "Cloro tradicional botella 900 ml"),
    ("Limpiapisos Lysoform 900ml",         "limpieza", 2290, "Limpiador desinfectante de pisos 900 ml"),
    ("Esponja Multiuso Scotch-Brite 3un",  "limpieza", 1490, "Esponjas multiuso pack 3 unidades"),
    ("Bolsa de Basura 50L 10un",           "limpieza", 1690, "Bolsas de basura 50 litros rollo 10 unidades"),
    ("Papel Toalla Nova 2 rollos",         "limpieza", 2790, "Papel toalla absorbente pack 2 rollos"),
]
