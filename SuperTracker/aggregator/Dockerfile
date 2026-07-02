FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aggregator.py .
COPY calibrar_matching.py .

CMD ["python", "-u", "aggregator.py"]
