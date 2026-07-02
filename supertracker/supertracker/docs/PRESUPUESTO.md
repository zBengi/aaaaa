# Presupuesto del proyecto — SuperTracker

> Corrige la observación de la Iteración 1: el documento de diseño no incluía un
> **presupuesto**. Aquí se estima el costo de poner en marcha y operar
> SuperTracker durante un año, separado en **hardware**, **energía**,
> **software/servicios** y **recurso humano**. Los montos están en **pesos
> chilenos (CLP)** y son estimaciones de referencia para fines académicos
> (valores aproximados de mercado a 2026).

## 1. Resumen ejecutivo

| Categoría | Costo inicial (una vez) | Costo anual recurrente |
|-----------|------------------------:|-----------------------:|
| Hardware (2 servidores) | $1.700.000 | — |
| Energía eléctrica | — | $315.000 |
| Software y servicios | $0 | $180.000 |
| Recurso humano (desarrollo) | $4.800.000 | — |
| Recurso humano (operación) | — | $1.440.000 |
| **Totales** | **$6.500.000** | **$1.935.000** |

**Costo total del primer año:** ≈ **$8.435.000 CLP**
**Costo de los años siguientes:** ≈ **$1.935.000 CLP/año**

> El grueso del costo inicial es el desarrollo (recurso humano). La operación es
> deliberadamente barata porque todo el stack es **software libre** y se
> autoaloja, sin licencias ni costos de nube por uso.

---

## 2. Hardware

El diseño contempla dos servidores físicos on-premise (ver
[`ARCHITECTURE.md`](ARCHITECTURE.md#5-modelo-de-despliegue-físico)).

| Ítem | Especificación | Cantidad | Precio unitario | Subtotal |
|------|----------------|:--------:|----------------:|---------:|
| Servidor de recolección | 8 cores, 16 GB RAM, 500 GB SSD | 1 | $850.000 | $850.000 |
| Servidor de consolidación/servicio | 8 cores, 16 GB RAM, 500 GB SSD | 1 | $850.000 | $850.000 |
| **Total hardware** | | | | **$1.700.000** |

> **Alternativa en la nube.** Dos VPS equivalentes (p. ej. 4 vCPU / 8 GB) cuestan
> del orden de **$35.000–$50.000 CLP/mes cada uno**, es decir **$840.000–
> $1.200.000 CLP/año** sin inversión inicial. Conviene si no se quiere mantener
> hardware propio; el costo se traslada de inicial a recurrente.

---

## 3. Energía eléctrica

Estimación para los dos servidores operando 24/7.

| Parámetro | Valor |
|-----------|------:|
| Consumo medio por servidor | 120 W |
| Consumo total (2 servidores) | 240 W = 0,24 kW |
| Horas al año | 8.760 h |
| Energía anual | 0,24 kW × 8.760 h ≈ **2.102 kWh** |
| Tarifa eléctrica (CL, ~$150/kWh) | $150/kWh |
| **Costo energético anual** | **≈ $315.000** |

---

## 4. Software y servicios

Todo el stack es **open source**, por lo que no hay costos de licencia.

| Componente | Licencia | Costo |
|------------|----------|------:|
| Python, FastAPI, Pydantic, SQLAlchemy, APScheduler | Open source (MIT/BSD/Apache) | $0 |
| RabbitMQ | Mozilla Public License | $0 |
| PostgreSQL 16 | PostgreSQL License | $0 |
| React, Vite, Recharts | MIT | $0 |
| Nginx, Traefik | BSD / MIT | $0 |
| Docker / Docker Compose | Apache 2.0 (uso bajo licencia gratuita) | $0 |
| **Subtotal licencias** | | **$0** |

Servicios recurrentes mínimos para operar en producción:

| Servicio | Detalle | Costo anual |
|----------|---------|------------:|
| Dominio web | `.cl` | ≈ $10.000 |
| Certificado TLS | Let's Encrypt (gratis vía Traefik) | $0 |
| Respaldo externo / almacenamiento | Object storage para backups de la BD | ≈ $50.000 |
| Conectividad / IP fija | Enlace para exponer el Servidor 2 | ≈ $120.000 |
| **Subtotal servicios** | | **≈ $180.000** |

---

## 5. Recurso humano

Estimación del esfuerzo de desarrollo del equipo de 4 integrantes y de la
operación posterior. Valor hora referencial de estudiante/desarrollador junior:
**$5.000 CLP/h**.

### Desarrollo (una vez)

| Fase | Horas estimadas | Costo |
|------|:---------------:|------:|
| Diseño y arquitectura | 160 | $800.000 |
| Implementación (scrapers, agregador, API, frontend) | 600 | $3.000.000 |
| Integración, pruebas y documentación | 200 | $1.000.000 |
| **Total desarrollo** | **960 h** | **$4.800.000** |

### Operación y mantenimiento (anual)

| Actividad | Horas/mes | Costo anual |
|-----------|:---------:|------------:|
| Monitoreo, mantención de scrapers y soporte | 24 | $1.440.000 |

> Los scrapers en modo `real` requieren mantención periódica porque los sitios
> de los supermercados cambian su HTML; ese es el principal costo operativo
> recurrente del sistema.

---

## 6. Notas y supuestos

- Montos en CLP, estimaciones de referencia 2026; no constituyen una cotización.
- No se incluye IVA.
- El presupuesto asume despliegue **on-premise**; la sección 2 ofrece la
  alternativa en nube.
- El costo de desarrollo se computa a valor de mercado aunque, en el contexto del
  curso, el trabajo lo realiza el propio equipo sin remuneración.
- El bajo costo recurrente (≈ $1,9M/año) es consecuencia directa de la decisión
  de usar exclusivamente software libre y autoalojamiento.
