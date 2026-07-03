"""
scraper_base.py – Clase base para todos los scrapers de SuperPrecios.

Responsabilidades:
  - Peticiones HTTP (GET/POST) con delays y headers de navegador.
  - Publicación de mensajes JSON en RabbitMQ (cola de trabajo).
  - Scheduling cada 1 hora mediante APScheduler.
  - Tasa de éxito: si cae por debajo del umbral se genera alerta en log.
"""

import json
import logging
import os
import time
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

import pika
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s – %(message)s",
)

# ── Umbral mínimo de tasa de éxito antes de alertar ──────────────
ALERT_THRESHOLD = 0.5   # 50 %

# ── Cabeceras HTTP base (genéricas) ───────────────────────────────
# IMPORTANTE: solo gzip/deflate. requests NO descomprime brotli (br) ni
# zstd sin librerías extra, y eso rompe resp.json() con basura binaria.
# Los headers específicos de cada sitio (Origin, Referer, Sec-Fetch-*)
# se pasan por scraper con extra_headers, porque cambian según el host.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


@dataclass
class PrecioMessage:
    """Esquema del mensaje JSON publicado en RabbitMQ."""
    supermercado: str
    nombre_producto: str
    categoria: str
    codigo_barra: Optional[str]
    precio: float
    url_producto: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class ScraperBase(ABC):
    """
    Clase base abstracta. Cada scraper concreto implementa
    `scrape()` y retorna una lista de PrecioMessage.
    """

    def __init__(self, nombre: str):
        self.nombre = nombre
        self.logger = logging.getLogger(nombre)

        # Configuración RabbitMQ desde variables de entorno
        self.rabbitmq_host  = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.rabbitmq_port  = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.queue_name     = os.getenv("RABBITMQ_QUEUE", "precios_queue")

        # Credenciales — ya NO se usa el usuario "guest" por defecto.
        rabbitmq_user = os.getenv("RABBITMQ_USER")
        rabbitmq_pass = os.getenv("RABBITMQ_PASS")
        if not rabbitmq_user or not rabbitmq_pass:
            raise RuntimeError(
                "RABBITMQ_USER y RABBITMQ_PASS son obligatorios "
                "(definir en .env.server1, no usar 'guest')."
            )
        self._credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)

        self._connection: Optional[pika.BlockingConnection] = None
        self._channel = None

    # ── Conexión RabbitMQ con reintentos ──────────────────────────

    def _connect_rabbitmq(self, retries: int = 5, delay: int = 5):
        for attempt in range(1, retries + 1):
            try:
                self.logger.info(
                    "Conectando a RabbitMQ %s:%d (intento %d/%d)…",
                    self.rabbitmq_host, self.rabbitmq_port, attempt, retries,
                )
                params = pika.ConnectionParameters(
                    host=self.rabbitmq_host,
                    port=self.rabbitmq_port,
                    credentials=self._credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300,
                )
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()
                self._channel.queue_declare(
                    queue=self.queue_name,
                    durable=True,   # mensajes persisten ante reinicios
                )
                self.logger.info("Conexión a RabbitMQ establecida.")
                return
            except pika.exceptions.AMQPConnectionError as exc:
                self.logger.warning("Fallo de conexión: %s", exc)
                if attempt < retries:
                    time.sleep(delay)
        raise RuntimeError(
            f"No se pudo conectar a RabbitMQ tras {retries} intentos."
        )

    def _ensure_connection(self):
        if self._connection is None or self._connection.is_closed:
            self._connect_rabbitmq()

    # ── Publicación de un mensaje ─────────────────────────────────

    def _publish(self, message: PrecioMessage):
        self._ensure_connection()
        self._channel.basic_publish(
            exchange="",
            routing_key=self.queue_name,
            body=message.to_json(),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                content_type="application/json",
            ),
        )

    # ── Núcleo HTTP unificado ─────────────────────────────────────

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        extra_headers: dict | None = None,
        timeout: int = 20,
    ) -> dict | list | None:
        """
        Petición HTTP con delay aleatorio (scraping responsable) que
        SIEMPRE registra el cuerpo de la respuesta ante un error HTTP.
        Devuelve el JSON parseado, o None ante cualquier fallo.
        """
        time.sleep(random.uniform(1, 3))
        headers = {**HEADERS, **(extra_headers or {})}
        try:
            resp = requests.request(
                method, url,
                headers=headers,
                params=params,
                json=json_body,
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            # Lo más importante para depurar: el cuerpo del 400/4xx.
            cuerpo = ""
            if exc.response is not None:
                cuerpo = exc.response.text[:400]
            self.logger.error(
                "HTTP %s %s → %s | cuerpo: %s",
                method, url,
                exc.response.status_code if exc.response is not None else "?",
                cuerpo,
            )
            return None
        except requests.RequestException as exc:
            self.logger.error("Error de red %s %s: %s", method, url, exc)
            return None
        except ValueError as exc:
            self.logger.error("Respuesta no es JSON válido en %s: %s", url, exc)
            return None

    # ── Wrappers que usan los scrapers concretos ──────────────────

    def get_page(self, url: str, extra_headers: dict | None = None) -> Optional[BeautifulSoup]:
        """Descarga HTML y devuelve un BeautifulSoup (para sitios SSR)."""
        time.sleep(random.uniform(1, 3))
        headers = {**HEADERS, **(extra_headers or {})}
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as exc:
            self.logger.error("Error al obtener %s: %s", url, exc)
            return None

    def get_json(self, url: str) -> dict | list | None:
        return self._request("GET", url)

    def get_json_params(self, url: str, params: dict) -> dict | list | None:
        return self._request("GET", url, params=params)

    def get_json_params_headers(
        self, url: str, params: dict, extra_headers: dict
    ) -> dict | list | None:
        return self._request("GET", url, params=params, extra_headers=extra_headers)

    def post_json(
        self, url: str, payload: dict, extra_headers: dict | None = None,
        params: dict | None = None,
    ) -> dict | list | None:
        headers = {"Content-Type": "application/json", **(extra_headers or {})}
        return self._request(
            "POST", url, params=params, json_body=payload, extra_headers=headers
        )

    # ── Ciclo principal ───────────────────────────────────────────

    def run_once(self):
        """Ejecuta el ciclo de scraping y publica los resultados."""
        self.logger.info("Iniciando ciclo de scraping…")
        mensajes = self.scrape()

        total      = len(mensajes)
        publicados = 0

        for msg in mensajes:
            try:
                self._publish(msg)
                publicados += 1
            except Exception as exc:
                self.logger.error("Error publicando mensaje: %s", exc)

        tasa = publicados / total if total else 0
        self.logger.info(
            "Ciclo completado: %d/%d mensajes publicados (tasa %.0f%%)",
            publicados, total, tasa * 100,
        )

        if total > 0 and tasa < ALERT_THRESHOLD:
            self.logger.critical(
                "⚠ ALERTA: tasa de éxito de scraping por debajo del umbral "
                "(%.0f%% < %.0f%%). Posible cambio en la API/HTML de %s.",
                tasa * 100, ALERT_THRESHOLD * 100, self.nombre,
            )

    def start_scheduler(self):
        """Arranca APScheduler: ejecuta run_once cada hora."""
        self._connect_rabbitmq()
        self.run_once()   # ejecución inmediata al iniciar

        scheduler = BlockingScheduler(timezone="America/Santiago")
        scheduler.add_job(
            self.run_once,
            trigger="interval",
            hours=1,
            id=f"scraper_{self.nombre}",
        )
        self.logger.info("Scheduler iniciado – próxima ejecución en 1 hora.")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Scheduler detenido.")

    # ── Método abstracto que cada scraper implementa ─────────────

    @abstractmethod
    def scrape(self) -> list[PrecioMessage]:
        """
        Extrae precios del supermercado correspondiente.
        Debe retornar una lista de PrecioMessage.
        """
