FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scraper_base.py .

COPY lider/scraper_lider.py .

CMD ["python", "-u", "scraper_lider.py"]
