FROM python:3.11-slim

WORKDIR /app

# Installeer de benodigdheden
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Start het commando (met reload aan voor lokaal ontwikkelen)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
