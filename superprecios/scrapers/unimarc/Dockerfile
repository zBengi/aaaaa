FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scraper_base.py .

COPY unimarc/scraper_unimarc.py .

CMD ["python", "-u", "scraper_unimarc.py"]
