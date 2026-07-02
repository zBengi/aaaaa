FROM python:3.11-slim

# Evita .pyc y fuerza logs sin buffer (mejor visibilidad en docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependencias primero para aprovechar la caché de capas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código del scraper.
COPY . .

# Usuario no root por seguridad.
RUN useradd --create-home appuser
USER appuser

CMD ["python", "scheduler.py"]
