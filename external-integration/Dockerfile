FROM python:3.11-slim

WORKDIR /app

RUN pip install pika pandas openpyxl

COPY . .

CMD ["python", "main.py"]