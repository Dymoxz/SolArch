import os
import json
import uuid
import pika

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://admin:admin_password@rabbitmq:5672/"
)


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)


def publish_payment_event(event_type: str, payment_id, payload: dict):

    connection = pika.BlockingConnection(
        pika.URLParameters(RABBITMQ_URL)
    )

    channel = connection.channel()

    channel.exchange_declare(
        exchange="payment_events_exchange",
        exchange_type="topic",
        durable=True
    )

    event_msg = {
        "event_type": event_type,
        "payment_id": payment_id,
        "data": payload
    }

    channel.basic_publish(
        exchange="payment_events_exchange",
        routing_key=f"payment.{event_type}",
        body=json.dumps(event_msg, cls=UUIDEncoder),
        properties=pika.BasicProperties(delivery_mode=2)
    )

    connection.close()