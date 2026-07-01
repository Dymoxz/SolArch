import os

import pika
from fastapi import FastAPI

app = FastAPI(title="Ball.com - Order Management API")


@app.get("/")
def read_root():
    return {"message": "Order Management API is online!"}


@app.get("/health/rabbitmq")
def check_rabbitmq():
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    try:
        parameters = pika.URLParameters(rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        connection.close()
        return {"status": "RabbitMQ is verbonden"}
    except Exception as e:
        return {"status": "Kan geen verbinding maken met RabbitMQ", "error": str(e)}
