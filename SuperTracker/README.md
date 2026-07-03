# SuperPrecios – Sistema Distribuido para Comparación de Precios

> Proyecto INFO288 · Universidad Austral de Chile
> Eduardo Leal · Benjamín Martínez · Luis Olivares

> **Versión final del proyecto.** Documento actualizado con la deduplicación
> del agregador y todos los controles de seguridad ya integrados.

---

## Descripción

Sistema distribuido que recopila, consolida y visualiza precios de productos en **Jumbo**, **Líder** y **Unimarc**. Permite buscar productos, comparar precios entre tiendas y consultar el historial de variaciones con gráficos.

---

## Arquitectura

```
┌──────────────── Servidor 1 ────────────────┐    ┌──────────────────── Servidor 2 ──────────────────────┐
│                                            │    │                                                      │
│  APScheduler (cada 1 hora)                 │    │  Traefik (ports 80/443, HTTPS)                       │
│       │                                    │    │       │                                              │
│  ┌────┴──────────────────────────────┐     │    │  ┌────┴──────────────────┐   ┌──────────────────┐    │
│  │  Scraper   Scraper   Scraper       │     │    │  │  Frontend React 18    │   │  API REST FastAPI │    │
│  │  Jumbo     Líder     Unimarc       │     │    │  │  (Nginx 1.25)         │   │  (uvicorn)        │    │
│  └────────────┬──────────────────────┘     │    │  └──────────────────────┘   └────────┬──────────┘    │
│               │ mensajes JSON              │    │                                       │              │
│          ┌────▼────┐                       │    │                              ┌────────▼──────────┐    │
│          │RabbitMQ │ ──────────────────────┼────┼──►  Servicio Agregador ──────►  PostgreSQL 16     │    │
│          │  3.12   │   (AMQP autenticado)  │    │     (Python + Pydantic)      │  supermercados     │    │
│          └─────────┘                       │    │                              │  productos         │    │
│                                            │    │                              │  precios           │    │
└────────────────────────────────────────────┘    └──────────────────────────────────────────────────────┘
```

**Patrón Pub/Sub:** los scrapers **publican** mensajes → RabbitMQ → el Agregador **consume**, deduplica y persiste → PostgreSQL. Cada componente autentica contra RabbitMQ con un usuario dedicado de mínimo privilegio (ver [Seguridad](#seguridad)).

---

## Estructura del Proyecto

```
superprecios/
├── docker-compose.server1.yml    # Scrapers + RabbitMQ
├── docker-compose.server2.yml    # API + Agregador + DB + Frontend + Traefik
│
├── .env.server1.example          # Plantilla de entorno (Servidor 1)
├── .env.server2.example          # Plantilla de entorno (Servidor 2)
├── .gitignore                    # Excluye .env reales, *.pem, *.key, acme.json
│
├── scrapers/
│   ├── scraper_base.py           # Clase base: HTTP, RabbitMQ (autenticado), APScheduler
│   ├── requirements.txt
│   ├── jumbo/     { scraper_jumbo.py, Dockerfile }
│   ├── lider/     { scraper_lider.py, Dockerfile }
│   └── unimarc/   { scraper_unimarc.py, Dockerfile }
│
├── aggregator/
│   ├── aggregator.py             # Consumidor RabbitMQ + dedup (TF-IDF/coseno) + persistencia
│   ├── calibrar_matching.py      # Calibra el umbral de deduplicación (herramienta de dev)
│   ├── requirements.txt
│   └── Dockerfile
│
├── api/
│   ├── main.py                   # API REST FastAPI (búsqueda por palabras + comparación + historial)
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/ { App.jsx, main.jsx, styles.css, hooks/useApi.js,
│   │          components/{SearchBar, ProductCard, PriceComparison, PriceHistoryChart},
│   │          pages/{Home, ProductDetail} }
│   ├── index.html, package.json, vite.config.js
│   ├── nginx.conf                # Cabeceras de seguridad + HSTS
│   └── Dockerfile
│
├── db/
│   └── init.sql                  # Tablas: supermercados, productos, precios + vista
│
├── rabbitmq/
│   └── init-users.sh             # Crea usuarios de mínimo privilegio (publisher/consumer)
│
└── traefik/
    └── dynamic.yml               # TLS options + middlewares (headers, rate limit)
```

---

## El Agregador — deduplicación de productos

El Agregador es un **consumidor RabbitMQ de un solo hilo** (`pika`) que, por cada mensaje: lo valida con **Pydantic** (`PrecioMessage`), resuelve a qué producto corresponde, y persiste el precio en PostgreSQL (`psycopg2`) conservando el historial completo. Reconecta automáticamente ante caídas transitorias del broker y reencola el mensaje si falla la persistencia (no se pierden datos).

### El problema

Cada supermercado nombra distinto el mismo producto y **no comparten un EAN confiable**:

```
"Leche Entera Colún 1 L"      (Jumbo)
"Leche Líquida Entera Colún UHT 1L"   (Líder)
"LECHE ENTERA COLUN 1LT"      (Unimarc)
```

Un puntaje difuso fijo no distingue las palabras que **importan** (marca, variante) de las de **relleno** (leche, botella, uht). La solución usa una técnica estándar de *record linkage*, determinista y sin dependencias de red.

### El pipeline (`resolver_producto_id`)

1. **Normalización del nombre** (`normalizar_nombre`), forma canónica que se compara entre tiendas:
   - minúsculas y sin tildes (`unicodedata` NFKD),
   - unidades unificadas (`1 lt`→`1l`, `kg`, `g`, `ml`, `cc`→`ml`, `pack de 6`/`x6`→`6un`),
   - sin puntuación,
   - se quitan *stopwords* de formato (`de`, `la`, `uht`, `liquida`, `botella`, `sachet`, `pote`…),
   - tokens **ordenados alfabéticamente** (así el orden de las palabras deja de importar).

2. **Coincidencia exacta** sobre el nombre normalizado. Si ya existe, se reutiliza ese producto.

3. **Similitud TF-IDF + coseno** si no hubo match exacto:
   - se construyen **n-gramas de caracteres** (n=3) del nombre normalizado,
   - se pondera con **TF-IDF** por categoría: los n-gramas poco frecuentes (marca, variante) **pesan más** que los comunes (`leche`, `agua`),
   - se compara con **distancia coseno** contra el catálogo de esa categoría,
   - **candado de medida:** si ambos nombres declaran cantidad y **no coinciden**, no se unen (`1kg` ≠ `3kg`),
   - si la mejor coincidencia supera `UMBRAL_SIMILITUD`, se reutiliza ese producto.

4. Si nada supera el umbral, se **crea un producto nuevo**.

### Umbral y calibración

`UMBRAL_SIMILITUD` (0.0–1.0, por defecto **0.65**) es configurable por variable de entorno. Más alto = más estricto = menos fusiones. Para elegirlo sin adivinar, `calibrar_matching.py` lee los productos **reales** de la base, calcula la similitud entre todos los pares de la misma categoría y reporta los pares que se unirían, los que quedan en zona límite y un histograma de puntajes (no modifica nada):

```bash
docker compose -f docker-compose.server2.yml exec aggregator python calibrar_matching.py
```

### Detalles de implementación

- **Migración idempotente al arranque** (`ensure_schema_and_backfill`): agrega la columna `nombre_normalizado` y su índice si no existen, y re-normaliza todos los productos ya cargados. Aplicar cambios de lógica no borra el volumen histórico.
- **Caché por categoría** con el IDF reconstruido al vuelo: como el consumidor es de un solo hilo, la caché es consistente y evita recalcular en cada mensaje.
- **Decisión de diseño:** se descartó usar un LLM para el matching — por mensaje sería lento, no determinista, caro y añadiría una dependencia de red frágil dentro de un servicio de streaming.

---

## Base de Datos (PostgreSQL 16)

| Tabla                | Columnas clave                                          | Descripción                              |
| -------------------- | ------------------------------------------------------- | ---------------------------------------- |
| `supermercados`      | id, nombre, url_base, activo                            | Cadenas monitoreadas                     |
| `productos`          | id, nombre, categoria, codigo_barra, `nombre_normalizado` | Catálogo unificado (col. normalizada para el matching) |
| `precios`            | id, producto_id, supermercado_id, precio, registrado_en | **Historial completo**                   |
| `v_precios_actuales` | (vista)                                                 | Precio más reciente por producto/tienda  |

Todas las consultas usan **parámetros enlazados** (`:tok0`, `:q`, …); no hay concatenación de input de usuario en SQL.

---

## API REST – Endpoints

| Método | Ruta                              | Descripción                                                    |
| ------ | --------------------------------- | -------------------------------------------------------------- |
| `GET`  | `/api/productos/buscar?q=leche`   | Búsqueda **por palabras** (AND, sin tildes) + precio mínimo actual |
| `GET`  | `/api/productos/{id}/comparar`    | Precios actuales en todas las tiendas                          |
| `GET`  | `/api/productos/{id}/historial`   | Historial con filtros de fecha/supermercado                    |
| `GET`  | `/api/supermercados`              | Lista de supermercados activos                                 |
| `GET`  | `/api/categorias`                 | Categorías disponibles                                         |
| `GET`  | `/health`                         | Health check                                                   |
| `GET`  | `/api/docs`                       | Swagger UI (FastAPI automático)                                |

La búsqueda separa la consulta en palabras normalizadas (sin tildes, minúsculas) y exige que **todas** aparezcan en el nombre (en cualquier orden), priorizando la frase exacta. Ej.: `leche loncoleche` encuentra *"Leche Entera Loncoleche Sin Tapa 1L"*.

---

## Despliegue

> ⚠️ Antes de desplegar, copia las plantillas de entorno y completa los valores
> reales. **Nunca se commitean los `.env.*` reales**, solo los `.example`.

### Servidor 1 (scrapers + RabbitMQ)

```bash
cp .env.server1.example .env.server1
# editar .env.server1 con contraseñas fuertes propias

docker compose -f docker-compose.server1.yml --env-file .env.server1 up -d --build
```

### Servidor 2 (API + DB + Frontend + Traefik)

```bash
cp .env.server2.example .env.server2
# editar .env.server2:
#   RABBITMQ_HOST          → IP privada/VPN del Servidor 1 (no pública)
#   RABBITMQ_CONSUMER_*    → deben coincidir con lo definido en .env.server1
#   TRAEFIK_DASHBOARD_HASH → generar con: htpasswd -nB admin
#   CORS_ALLOWED_ORIGINS   → dominio real del frontend (no "*")

docker compose -f docker-compose.server2.yml --env-file .env.server2 up -d --build
```

### Verificar / operar

```bash
docker compose -f docker-compose.server1.yml ps
docker compose -f docker-compose.server2.yml logs -f aggregator

# https://<TRAEFIK_DOMAIN>/api/docs   → API (HTTPS con Let's Encrypt)
# https://<TRAEFIK_DOMAIN>            → Frontend
# https://traefik.<TRAEFIK_DOMAIN>    → Dashboard de Traefik (usuario/clave)
```

La Management UI de RabbitMQ (`15672`) ya **no** se publica al exterior; solo es accesible desde el propio Servidor 1 (`127.0.0.1:15672`) o vía túnel SSH:

```bash
ssh -L 15672:localhost:15672 usuario@servidor1   # luego http://localhost:15672
```

---

## Seguridad

Controles aplicados para llevar el sistema a un estado desplegable de forma razonablemente segura. Están organizados por área; cada uno incluye el *por qué*.

### 1. Gestión de secretos

- Todas las credenciales (Postgres, RabbitMQ, Traefik) viven en `.env.server1` / `.env.server2`, **excluidos por `.gitignore`**; solo se versionan los `.example`. Evita que las credenciales terminen en el historial de git (CWE-798).
- Las contraseñas reales se generan con `secrets.token_urlsafe` (**192 bits de entropía**), no triviales ni por defecto.
- Se eliminaron los **fallbacks hardcodeados** de `DATABASE_URL` en `api/main.py` y `aggregator/aggregator.py`: ahora, si la variable no está seteada, el servicio lanza `RuntimeError` en vez de arrancar con una credencial embebida. Falla explícita > falla silenciosa insegura.
- Los `docker-compose` referencian las credenciales como `${VAR:?falta …}` (obligatorias, sin default), de modo que los YAML quedan libres de secretos y auditables.

### 2. Autenticación y mínimo privilegio (RabbitMQ)

- Se **elimina el usuario `guest`** (público y conocido). `rabbitmq/init-users.sh` crea dos usuarios dedicados vía la API de management:
  - **publisher** (scrapers): solo *write* en `precios_queue`.
  - **consumer** (agregador): solo *read* en `precios_queue`.
- Un servicio `rabbitmq-init` corre una sola vez **antes** de los scrapers (`depends_on: service_completed_successfully`), garantizando que los usuarios existan antes de cualquier autenticación (evita condiciones de carrera).
- `scraper_base.py` y `aggregator.py` se conectan con `pika.PlainCredentials` y **fallan si faltan las credenciales**. Si un scraper se compromete, el impacto se acota a "escribir mensajes falsos", no a administrar el broker.

### 3. Superficie de red

- La Management UI de RabbitMQ se publica solo en `127.0.0.1:15672` (antes `15672:15672`, alcanzable por cualquiera en la red).
- Traefik **sin** `--api.insecure=true` ni puerto `8080`: su dashboard ya no expone rutas internas, IPs de contenedores ni topología.
- PostgreSQL **sin `ports:`** publicados al host: solo accesible dentro de la red interna `app_net`.

### 4. Cifrado en tránsito (TLS/HTTPS)

- Traefik con **Let's Encrypt** (`acme.httpchallenge`) y redirección forzada HTTP → HTTPS. Antes el entrypoint `websecure` estaba declarado sin certificado y el tráfico iba en texto plano.
- API y frontend responden **solo sobre HTTPS** (`entrypoints=websecure` + `tls.certresolver=letsencrypt`).
- `traefik/dynamic.yml` fija **TLS 1.2+** con cifrados modernos (ECDHE/GCM), evitando downgrade a TLS 1.0/1.1 (protección contra BEAST, POODLE).
- `HSTS` (`max-age=63072000; includeSubDomains`) en `nginx.conf`: el navegador no vuelve a intentar HTTP con este dominio (anti SSL-stripping).

### 5. Control de acceso a la API

- **CORS restringido** a los orígenes de `CORS_ALLOWED_ORIGINS` (antes era `"*"`, que permite requests desde cualquier sitio en el navegador del usuario).
- **Rate limiting en dos capas:** Traefik (`api-ratelimit`, 60 req/min, burst 30) y `slowapi` dentro de FastAPI (60/min global, **20/min** en `/api/productos/buscar`, el endpoint más costoso por su `LIKE` con posible full scan). Defensa en profundidad contra DoS.
- **Validación de parámetros:** `q` y `categoria` con `max_length=100`, `pagina ≤ 1000`. Evita payloads que fuercen queries costosas o exploten la paginación.

### 6. Cabeceras de seguridad HTTP

Aplicadas en **tres niveles** (defensa en profundidad): Nginx, Traefik y la propia API.

- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`, `Referrer-Policy`, `Permissions-Policy`.
- `server_tokens off` en Nginx oculta la versión exacta del servidor.
- La API agrega sus propias cabeceras vía middleware, por si alguna vez se expusiera sin pasar por Traefik/Nginx.

### 7. Endurecimiento de contenedores (CIS Benchmark)

- **Usuario no-root** (`USER app`) en todas las imágenes propias (API, agregador, scrapers). Limita el daño y dificulta un *container escape* si se ejecuta código malicioso dentro.
- `read_only: true` + `tmpfs: [/tmp]` + `cap_drop: [ALL]` en los servicios que no necesitan escribir en disco: impide persistir malware y retira capabilities innecesarias.
- **Límites de CPU/memoria** (`deploy.resources.limits`) en cada servicio: un contenedor con fuga de memoria o un pico de tráfico no puede agotar el host y tumbar al resto (DoS por "vecino ruidoso").
- **Docker socket protegido:** Traefik ya no monta `/var/run/docker.sock` directo; pasa por `docker-socket-proxy` con solo lectura de contenedores/redes (`CONTAINERS=1, NETWORKS=1, POST=0`). Montar el socket es una vía conocida de escape de contenedor a host.

### 8. Base de datos

- **Sin SQL injection:** las queries usan parámetros enlazados; se verificó que no hay concatenación de input de usuario (control ya presente, documentado).
- El `healthcheck` de Postgres usa variables (`$${POSTGRES_USER}/$${POSTGRES_DB}`) en vez de literales, evitando *drift* con las credenciales reales.

### Limitaciones conocidas

Fuera del alcance de la implementación actual (se documentan para no perder el contexto):

- Rotación periódica de credenciales.
- Backups cifrados automáticos de PostgreSQL.
- Firma criptográfica de los mensajes de RabbitMQ: hoy Pydantic valida la **forma** del mensaje, no la **autenticidad** del origen.
- TLS en la propia conexión AMQP y JWT para autenticar clientes de la API.
- Si el Servidor 1 y el Servidor 2 están en redes públicas distintas, el tráfico AMQP entre ellos **debe** ir sobre una VPN (WireGuard) o túnel SSH: las Docker networks no cruzan hosts físicos por sí solas.

---

## Scraping Responsable

- Delay aleatorio de 1–3 s entre peticiones (evita sobrecargar el sitio objetivo).
- User-Agent identificado como bot (`SuperPreciosBot/1.0`).
- **Alerta automática:** si la tasa de éxito de extracción cae por debajo del 50 %, se emite un log `CRITICAL` (posible cambio en la estructura HTML del sitio).
- Selectores/rutas de parsing definidos al inicio de cada scraper para facilitar su actualización.

---

## Tecnologías

| Componente         | Tecnología                          | Versión            |
| ------------------ | ----------------------------------- | ------------------ |
| Scrapers           | Python + requests + BeautifulSoup4  | 3.11 / 2.31 / 4.12 |
| Scheduler          | APScheduler                         | 3.10               |
| Message broker     | RabbitMQ                            | 3.12               |
| Agregador          | Python + pika + psycopg2 + Pydantic | 2.6                |
| Base de datos      | PostgreSQL                          | 16                 |
| API REST           | FastAPI + uvicorn + slowapi         | 0.110 / 0.29       |
| ORM                | SQLAlchemy                          | 2.0                |
| Frontend           | React + Recharts                    | 18 / 2.12          |
| Servidor estático  | Nginx                               | 1.25               |
| Reverse proxy      | Traefik                             | 2.11               |
| Contenedores       | Docker + Compose                    | 26.0 / 2.26        |

Todo software libre, sin licencias comerciales.