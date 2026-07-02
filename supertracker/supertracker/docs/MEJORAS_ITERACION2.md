# Mejoras de la Iteración 2 respecto de la Iteración 1

> Este documento resume los cambios introducidos en la Iteración 2, tanto los que
> responden a la **retroalimentación de los evaluadores** como las **decisiones de
> diseño** tomadas durante la implementación.
>
> ⚠️ **Importante:** estas mejoras deben quedar reflejadas también en el
> **documento de especificación (informe LaTeX)** de la Iteración 2, no solo en el
> repositorio. Esta es una exigencia explícita del enunciado ("las mejoras deben
> verse reflejadas en el documento de especificación"). La tabla de la sección 1
> sirve de checklist para esa actualización.

## 1. Correcciones a la retroalimentación de la Iteración 1

| # | Observación del evaluador | Cómo se resolvió | Dónde |
|---|---------------------------|------------------|-------|
| 1 | Faltaba el **presupuesto** | Presupuesto completo: hardware, energía, software/servicios y recurso humano, con alternativa on-premise vs nube | [`PRESUPUESTO.md`](PRESUPUESTO.md) |
| 2 | No se mencionaba el **nombre del proyecto** ("SuperTracker") en el informe | El nombre encabeza el README y toda la documentación; debe añadirse al informe LaTeX | [`README`](../README.md), todo `docs/` |
| 3 | Faltaban **diagramas de secuencia** | Dos diagramas de secuencia: ingesta de precios y consulta del usuario | [`README`](../README.md#-arquitectura) |
| 4 | Faltaba **diagrama ER / relacional** | Diagrama ER + diccionario de datos completo | [`README`](../README.md), [`ARCHITECTURE.md`](ARCHITECTURE.md#7-modelo-relacional) |
| 5 | El **diagrama de componentes** debía usar **notación UML** | Diagrama de componentes con estereotipos `«component»`/`«container»` e interfaces *provided/required* | [`ARCHITECTURE.md`](ARCHITECTURE.md#3-diagrama-de-componentes-uml) |
| 6 | Los **contenedores Docker** debían aparecer en los diagramas | Todos los diagramas (componentes, despliegue, físico) marcan cada contenedor con `«container»`/`«artifact»` | [`README`](../README.md), [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| 7 | Faltaba **explicar en detalle cada pieza** de la arquitectura | Sección con rol, funcionamiento interno y justificación de cada componente | [`ARCHITECTURE.md`](ARCHITECTURE.md#4-explicación-detallada-de-cada-componente) |
| 8 | Faltaba detallar la **escalabilidad** (componentes, estrategia, límites, métricas) | Documento dedicado: qué escala, cómo, límites actuales y métricas | [`ESCALABILIDAD.md`](ESCALABILIDAD.md) |

## 2. Decisiones de diseño de la implementación

### 2.1 Campo `categoria` en el contrato de mensajes
Se añadió un campo opcional `categoria` al mensaje JSON de RabbitMQ para poder
poblar la columna `producto.categoria` (que es `NOT NULL` según el diccionario de
datos). El cambio es **retro-compatible**: si el mensaje no trae el campo, el
agregador asume el valor `"general"`. Así la búsqueda por categoría funciona sin
romper el contrato original.

### 2.2 Modos de scraping `mock` y `real`
Los scrapers tienen dos modos seleccionables por la variable `SCRAPER_MODE`:

- **`mock`** (por defecto): genera precios sintéticos a partir de un catálogo
  semilla determinista.
- **`real`**: scraping HTTP real con `requests` + `BeautifulSoup`.

**Justificación.** El modo `mock` permite una demostración **end-to-end
reproducible** de todo el sistema distribuido (Pub/Sub, persistencia, API,
frontend) sin depender de la disponibilidad ni de los cambios de HTML de los
sitios reales —que son frágiles y cambian sin aviso—. El foco de la asignatura es
la **arquitectura distribuida**, no la robustez del scraping; el modo `real`
queda implementado y disponible para uso real. Es una decisión consciente,
documentada honestamente, no una limitación oculta.

### 2.3 Idempotencia para escritura concurrente
La resolución de productos y supermercados usa `INSERT ... ON CONFLICT DO
NOTHING`, de modo que varias réplicas del agregador pueden escribir en paralelo
sin generar duplicados. Esto habilita el escalado horizontal del agregador
descrito en [`ESCALABILIDAD.md`](ESCALABILIDAD.md).

### 2.4 Separación lectura/escritura
La **escritura** (agregador) y la **lectura** (API REST) son servicios
**separados**, aunque ambos sean FastAPI. Esto permite escalar cada flujo de
forma independiente y restringir los permisos: la API es de solo lectura
(incluido CORS limitado a `GET`).

### 2.5 Traefik como API Gateway
Se incorporó **Traefik** como *reverse proxy* y punto de entrada único: enruta
`/api` a la API y `/` al frontend, unificando el acceso bajo un solo origen,
ocultando la topología interna y sirviendo de balanceador cuando hay réplicas.

### 2.6 Redes Docker que reflejan los dos servidores
El `docker-compose.yml` define redes separadas (`collection`, `backbone`, `data`,
`edge`) que reflejan el modelo físico de dos servidores del diseño, de modo que
pasar a un despliegue en dos máquinas sea un cambio de **configuración** y no de
arquitectura.

## 3. Estado de la implementación

| Funcionalidad principal | Estado |
|-------------------------|:------:|
| Recolección periódica por tienda | ✅ |
| Publicación asíncrona vía RabbitMQ | ✅ |
| Consumo, validación y persistencia | ✅ |
| Historial completo de precios | ✅ |
| Búsqueda por nombre y categoría | ✅ |
| Comparación de precios entre tiendas | ✅ |
| Historial con gráfico | ✅ |
| Cálculo del más barato y del ahorro | ✅ |
| Estadísticas globales | ✅ |
| Interfaz web responsive | ✅ |
| Enrutamiento por reverse proxy | ✅ |

Todas las funcionalidades principales (no relacionadas con seguridad) del diseño
están implementadas. La lógica de backend (agregador + API) fue validada contra
una base PostgreSQL real y el frontend compila sin errores.
