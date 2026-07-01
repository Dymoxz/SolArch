FROM python:3.11-slim

WORKDIR /app

# Installeer de benodigdheden
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Start het commando op poort 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]
