# SuperPrecios – Sistema Distribuido para Comparación de Precios

> Proyecto INFO288 · Universidad Austral de Chile
> Eduardo Leal · Benjamín Martínez · Luis Olivares

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

**Deduplicación de productos:** como cada tienda nombra distinto el mismo producto y no comparten un EAN confiable, el Agregador unifica registros con **TF-IDF sobre n-gramas de caracteres + similitud coseno** (umbral configurable `UMBRAL_SIMILITUD`, por defecto `0.65`; calibrable con `aggregator/calibrar_matching.py`). Primero intenta coincidencia exacta por nombre normalizado y, si no, la mejor coincidencia por coseno que supere el umbral.

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
│   ├── aggregator.py             # Consumidor RabbitMQ + dedup (TF-IDF/coseno) + persistencia
│   ├── calibrar_matching.py      # Calibra el umbral de deduplicación (dev)
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
├── rabbitmq/
│   └── init-users.sh             # Crea usuarios de mínimo privilegio (publisher/consumer)
│
└── traefik/
    └── dynamic.yml
```

---

## Base de Datos (PostgreSQL 16)

| Tabla                  | Columnas clave                                          | Descripción                             |
| ---------------------- | ------------------------------------------------------- | ---------------------------------------- |
| `supermercados`      | id, nombre, url_base, activo                            | Cadenas monitoreadas                     |
| `productos`          | id, nombre, categoria, codigo_barra                     | Catálogo unificado                      |
| `precios`            | id, producto_id, supermercado_id, precio, registrado_en | **Historial completo**             |
| `v_precios_actuales` | (vista)                                                 | Precio más reciente por producto/tienda |

---

## API REST – Endpoints

| Método | Ruta                              | Descripción                                |
| ------- | --------------------------------- | ------------------------------------------- |
| `GET` | `/api/productos/buscar?q=leche` | Búsqueda por palabras (AND, sin tildes) + precio mínimo actual |
| `GET` | `/api/productos/{id}/comparar`  | Precios actuales en todas las tiendas       |
| `GET` | `/api/productos/{id}/historial` | Historial con filtros de fecha/supermercado |
| `GET` | `/api/supermercados`            | Lista de supermercados activos              |
| `GET` | `/api/categorias`               | Categorías disponibles                     |
| `GET` | `/health`                       | Health check                                |
| `GET` | `/api/docs`                     | Swagger UI (FastAPI automático)            |

---

## Despliegue

> ⚠️ Antes de desplegar, copia las plantillas de entorno y completa los
> valores reales — **nunca se commitean los `.env.*` reales**, solo los
> `.example`.

### Servidor 1 (scrapers + RabbitMQ)

```bash
cp .env.server1.example .env.server1
# editar .env.server1 con contraseñas fuertes propias

docker compose -f docker-compose.server1.yml --env-file .env.server1 up -d
```

### Servidor 2 (API + DB + Frontend + Traefik)

```bash
cp .env.server2.example .env.server2
# editar .env.server2:
#   - RABBITMQ_HOST         → IP privada/VPN real del Servidor 1 (no pública)
#   - RABBITMQ_CONSUMER_*   → deben coincidir con lo definido en .env.server1
#   - TRAEFIK_DASHBOARD_HASH → generar con: htpasswd -nB admin  (o "openssl passwd -apr1")
#   - CORS_ALLOWED_ORIGINS  → dominio real del frontend (no "*")

docker compose -f docker-compose.server2.yml --env-file .env.server2 up -d
```

### Verificar

```bash
# API docs (detrás de Traefik, HTTPS con Let's Encrypt)
https://<TRAEFIK_DOMAIN>/api/docs

# Frontend
https://<TRAEFIK_DOMAIN>

# Dashboard de Traefik (requiere usuario/clave)
https://traefik.<TRAEFIK_DOMAIN>
```

La Management UI de RabbitMQ (`15672`) ya **no** se publica al exterior;
solo es accesible desde el propio Servidor 1 (`127.0.0.1:15672`) o vía
túnel SSH: `ssh -L 15672:localhost:15672 usuario@servidor1`.

---

## Seguridad

Cambios aplicados sobre el diseño original para llevarlo a un estado
desplegable de forma razonablemente segura:

- **Secretos fuera del repo:** todas las credenciales (Postgres, RabbitMQ,
  Traefik) viven en `.env.server1` / `.env.server2`, excluidos por
  `.gitignore`. Solo se versionan los `.example`.
- **RabbitMQ sin usuario `guest`:** se crean usuarios dedicados de mínimo
  privilegio vía `rabbitmq/init-users.sh` — el *publisher* (scrapers) solo
  puede escribir en `precios_queue`, el *consumer* (agregador) solo puede
  leerla. El usuario admin no se comparte con las aplicaciones.
- **HTTPS real con Traefik:** certificados automáticos vía Let's Encrypt
  (`certresolver`), redirección forzada HTTP → HTTPS, TLS 1.2+ con cifrados
  modernos (`traefik/dynamic.yml`).
- **Dashboard de Traefik protegido:** ya no usa `--api.insecure=true`; se
  sirve solo por HTTPS, en un subdominio propio, con `basicAuth`.
- **Docker socket protegido:** Traefik ya no monta `/var/run/docker.sock`
  directo; pasa por `docker-socket-proxy`, que expone solo lectura de
  contenedores/redes (sin permisos de escritura sobre el daemon).
- **CORS restringido** a los orígenes definidos en `CORS_ALLOWED_ORIGINS`
  (antes era `"*"`).
- **Rate limiting** en dos capas: Traefik (`api-ratelimit`, 60 req/min) y
  `slowapi` dentro de FastAPI (20 req/min en `/api/productos/buscar`, el
  endpoint más costoso por su `ILIKE`).
- **Cabeceras de seguridad HTTP** (`CSP`, `HSTS`, `X-Frame-Options`,
  `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`) en
  Nginx, Traefik y la API.
- **Contenedores hardened:** usuario no-root en todas las imágenes propias
  (API, agregador, scrapers), `read_only: true` + `cap_drop: [ALL]` donde
  el proceso no necesita escribir en disco, y límites de CPU/memoria en
  todos los servicios para evitar que un contenedor caído tumbe el host.
- **PostgreSQL** sin puertos publicados al host: solo accesible dentro de
  `app_net`.

### Pendiente / fuera de alcance de esta iteración

- Rotación periódica de credenciales.
- Backups cifrados automáticos de PostgreSQL.
- WAF / detección de anomalías sobre los logs de Traefik.
- Firma criptográfica de los mensajes de RabbitMQ (hoy solo se valida
  forma con Pydantic, no autenticidad del origen).
- Si el Servidor 1 y el Servidor 2 están en redes públicas distintas, el
  tráfico AMQP entre ellos debe ir sobre una VPN (WireGuard) o túnel SSH:
  Docker networks no cruzan hosts físicos por sí solas.

---

## Scraping Responsable

- Delay aleatorio de 1–3 s entre peticiones (evita sobrecarga del servidor objetivo).
- User-Agent identificado como bot (`SuperPreciosBot/1.0`).
- **Alerta automática:** si la tasa de éxito de extracción cae por debajo del 50%, se genera un log `CRITICAL` indicando posible cambio en la estructura HTML del sitio.
- Selectores CSS definidos como constantes al inicio de cada scraper para facilitar actualización.

---

## Tecnologías

| Componente         | Tecnología                        | Versión           |
| ------------------ | ---------------------------------- | ------------------ |
| Scrapers           | Python + requests + BeautifulSoup4 | 3.11 / 2.31 / 4.12 |
| Scheduler          | APScheduler                        | 3.10               |
| Message broker     | RabbitMQ                           | 3.12               |
| Agregador          | FastAPI + Pydantic                 | 0.110 / 2.6        |
| Base de datos      | PostgreSQL                         | 16                 |
| API REST           | FastAPI + uvicorn                  | 0.110 / 0.29       |
| ORM                | SQLAlchemy                         | 2.0                |
| Frontend           | React + Recharts                   | 18 / 2.12          |
| Servidor estático | Nginx                              | 1.25               |
| Reverse proxy      | Traefik                            | 2.11               |
| Contenedores       | Docker + Compose                   | 26.0 / 2.26        |

Todo software libre, sin licencias comerciales.

---

## Trabajo Futuro (Iteraciones 2 y 3)

- Implementación completa con sitios reales (ajuste de selectores CSS).
- TLS en comunicación con RabbitMQ.
- JWT para autenticación de la API REST.
- Validación experimental de métricas: latencia, tasa de scraping, carga concurrente (50 usuarios).
- Notificaciones de baja de precio (evaluado para Iteración 3).
- Migración de Docker Compose a Kubernetes si la demanda lo requiere.
