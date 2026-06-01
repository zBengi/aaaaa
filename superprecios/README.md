# SuperPrecios – Sistema Distribuido para Comparación de Precios

> Proyecto INFO288 · Universidad Austral de Chile  
> Eduardo Leal · Benjamín Martínez · Luis Olivares · Ninoska Toledo

---

## Descripción

Sistema distribuido que recopila, consolida y visualiza precios de productos en **Jumbo**, **Líder** y **Unimarc** en tiempo real. Permite buscar productos, comparar precios entre tiendas y consultar el historial de variaciones con gráficos.

---

## Arquitectura

```
┌──────────────── Servidor 1 ────────────────┐    ┌──────────────────── Servidor 2 ──────────────────────┐
│                                            │    │                                                      │
│  APScheduler (cada 1 hora)                 │    │  Traefik (ports 80/443)                              │
│       │                                   │    │       │                                               │
│  ┌────┴──────────────────────────────┐    │    │  ┌────┴──────────────────┐   ┌──────────────────┐    │
│  │  Scraper   Scraper   Scraper      │    │    │  │  Frontend React 18    │   │  API REST FastAPI │    │
│  │  Jumbo     Líder     Unimarc      │    │    │  │  (Nginx 1.25)         │   │  (uvicorn)        │    │
│  └────────────┬──────────────────────┘    │    │  └──────────────────────┘   └────────┬──────────┘    │
│               │ JSON messages             │    │                                       │               │
│          ┌────▼────┐                      │    │                              ┌────────▼──────────┐    │
│          │RabbitMQ │ ─────────────────────┼────┼──► Servicio Agregador ──────► PostgreSQL 16      │    │
│          │  3.12   │   red interna        │    │     (FastAPI+Pydantic)       │  supermercados     │    │
│          └─────────┘                      │    │                              │  productos         │    │
│                                            │    │                              │  precios           │    │
└────────────────────────────────────────────┘    └──────────────────────────────────────────────────────┘
```

**Patrón Pub/Sub:** scrapers publican → RabbitMQ → Agregador consume → PostgreSQL.

---

## Estructura del Proyecto

```
superprecios/
├── docker-compose.server1.yml    # Scrapers + RabbitMQ
├── docker-compose.server2.yml    # API + Agregador + DB + Frontend + Traefik
│
├── scrapers/
│   ├── scraper_base.py           # Clase base: HTTP, RabbitMQ, APScheduler
│   ├── requirements.txt
│   ├── jumbo/
│   │   ├── scraper_jumbo.py
│   │   └── Dockerfile
│   ├── lider/
│   │   ├── scraper_lider.py
│   │   └── Dockerfile
│   └── unimarc/
│       ├── scraper_unimarc.py
│       └── Dockerfile
│
├── aggregator/
│   ├── aggregator.py             # Consumidor RabbitMQ + persistencia PostgreSQL
│   ├── requirements.txt
│   └── Dockerfile
│
├── api/
│   ├── main.py                   # API REST FastAPI (5 endpoints)
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Router principal
│   │   ├── main.jsx
│   │   ├── styles.css            # Diseño responsive (mobile-first)
│   │   ├── hooks/useApi.js       # Cliente Axios centralizado
│   │   ├── components/
│   │   │   ├── SearchBar.jsx
│   │   │   ├── ProductCard.jsx
│   │   │   ├── PriceComparison.jsx
│   │   │   └── PriceHistoryChart.jsx  # Recharts
│   │   └── pages/
│   │       ├── Home.jsx          # Búsqueda + resultados paginados
│   │       └── ProductDetail.jsx # Comparación + historial con gráfico
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf
│   └── Dockerfile
│
├── db/
│   └── init.sql                  # Tablas: supermercados, productos, precios + vista
│
└── traefik/
    └── dynamic.yml
```

---

## Base de Datos (PostgreSQL 16)

| Tabla | Columnas clave | Descripción |
|-------|---------------|-------------|
| `supermercados` | id, nombre, url_base, activo | Cadenas monitoreadas |
| `productos` | id, nombre, categoria, codigo_barra | Catálogo unificado |
| `precios` | id, producto_id, supermercado_id, precio, registrado_en | **Historial completo** |
| `v_precios_actuales` | (vista) | Precio más reciente por producto/tienda |

---

## API REST – Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/productos/buscar?q=leche` | Búsqueda full-text + precio mínimo actual |
| `GET` | `/api/productos/{id}/comparar` | Precios actuales en todas las tiendas |
| `GET` | `/api/productos/{id}/historial` | Historial con filtros de fecha/supermercado |
| `GET` | `/api/supermercados` | Lista de supermercados activos |
| `GET` | `/api/categorias` | Categorías disponibles |
| `GET` | `/health` | Health check |
| `GET` | `/api/docs` | Swagger UI (FastAPI automático) |

---

## Despliegue

### Servidor 1 (scrapers + RabbitMQ)
```bash
docker compose -f docker-compose.server1.yml up -d
```

### Servidor 2 (API + DB + Frontend + Traefik)
```bash
# Ajustar RABBITMQ_HOST en docker-compose.server2.yml con la IP real del Servidor 1
docker compose -f docker-compose.server2.yml up -d
```

### Verificar
```bash
# RabbitMQ Management UI
http://localhost:15672   # usuario: guest / pass: guest

# API docs
http://superprecios.local/api/docs

# Frontend
http://superprecios.local
```

---

## Scraping Responsable

- Delay aleatorio de 1–3 s entre peticiones (evita sobrecarga del servidor objetivo).
- User-Agent identificado como bot (`SuperPreciosBot/1.0`).
- **Alerta automática:** si la tasa de éxito de extracción cae por debajo del 50%, se genera un log `CRITICAL` indicando posible cambio en la estructura HTML del sitio.
- Selectores CSS definidos como constantes al inicio de cada scraper para facilitar actualización.

---

## Tecnologías

| Componente | Tecnología | Versión |
|-----------|-----------|---------|
| Scrapers | Python + requests + BeautifulSoup4 | 3.11 / 2.31 / 4.12 |
| Scheduler | APScheduler | 3.10 |
| Message broker | RabbitMQ | 3.12 |
| Agregador | FastAPI + Pydantic | 0.110 / 2.6 |
| Base de datos | PostgreSQL | 16 |
| API REST | FastAPI + uvicorn | 0.110 / 0.29 |
| ORM | SQLAlchemy | 2.0 |
| Frontend | React + Recharts | 18 / 2.12 |
| Servidor estático | Nginx | 1.25 |
| Reverse proxy | Traefik | 2.11 |
| Contenedores | Docker + Compose | 26.0 / 2.26 |

Todo software libre, sin licencias comerciales.

---

## Trabajo Futuro (Iteraciones 2 y 3)

- Implementación completa con sitios reales (ajuste de selectores CSS).
- TLS en comunicación con RabbitMQ.
- JWT para autenticación de la API REST.
- Validación experimental de métricas: latencia, tasa de scraping, carga concurrente (50 usuarios).
- Notificaciones de baja de precio (evaluado para Iteración 3).
- Migración de Docker Compose a Kubernetes si la demanda lo requiere.
