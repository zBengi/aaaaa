FROM python:3.11-slim

WORKDIR /app

# requirements.txt y scraper_base.py están en la raíz del contexto (scrapers/)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scraper_base.py .

# Scraper específico
COPY jumbo/scraper_jumbo.py .

CMD ["python", "-u", "scraper_jumbo.py"]
