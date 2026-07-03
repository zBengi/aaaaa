FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aggregator.py .
COPY calibrar_matching.py .

# Usuario no-root
RUN useradd --create-home --shell /usr/sbin/nologin app \
    && chown -R app:app /app
USER app

CMD ["python", "-u", "aggregator.py"]
