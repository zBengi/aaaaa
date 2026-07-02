"""Entrypoint del contenedor de scraping.

Selecciona el scraper según la variable de entorno ``STORE`` y lo ejecuta
periódicamente con APScheduler (cada ``SCRAPE_INTERVAL_MINUTES``). Cada cadena
corre en su propio contenedor, de forma totalmente independiente: la caída de
uno no afecta a los demás (requisito de bajo acoplamiento del diseño).
"""
from __future__ import annotations

import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler

from jumbo_scraper import JumboScraper
from lider_scraper import LiderScraper
from shared import config
from shared.publisher import RabbitPublisher
from unimarc_scraper import UnimarcScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scraper.main")

SCRAPERS = {
    "jumbo": JumboScraper,
    "lider": LiderScraper,
    "unimarc": UnimarcScraper,
}


def main() -> None:
    store = config.STORE
    scraper_cls = SCRAPERS.get(store)
    if scraper_cls is None:
        logger.error("STORE='%s' no es válido. Opciones: %s", store, list(SCRAPERS))
        sys.exit(1)

    publisher = RabbitPublisher()
    publisher.connect()
    scraper = scraper_cls(publisher)

    logger.info(
        "Scraper '%s' iniciado | intervalo=%s min | modo=%s",
        scraper.store_name, config.SCRAPE_INTERVAL_MINUTES, config.SCRAPER_MODE,
    )

    if config.RUN_ON_STARTUP:
        scraper.run_once()

    scheduler = BlockingScheduler(timezone="America/Santiago")
    scheduler.add_job(
        scraper.run_once,
        trigger="interval",
        minutes=config.SCRAPE_INTERVAL_MINUTES,
        id=f"scrape_{store}",
        max_instances=1,
        coalesce=True,
    )

    # Apagado limpio ante SIGTERM/SIGINT (docker stop).
    def _shutdown(signum, _frame):
        logger.info("Señal %s recibida; deteniendo scheduler…", signum)
        scheduler.shutdown(wait=False)
        publisher.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        publisher.close()


if __name__ == "__main__":
    main()
