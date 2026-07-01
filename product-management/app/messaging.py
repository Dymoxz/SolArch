import os
import json
import uuid
import pika
from uuid import UUID

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://admin:admin_password@rabbitmq:5672/"
)


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)


def publish_product_event(event_type: str, product_id: UUID, payload: dict):

    try:
        parameters = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        channel.exchange_declare(
            exchange='product_events_exchange',
            exchange_type='topic',
            durable=True
        )

        event_msg = {
            "event_type": event_type,
            "product_id": product_id,
            "data": payload
        }

        channel.basic_publish(
            exchange='product_events_exchange',
            routing_key=f"product.{event_type}",
            body=json.dumps(event_msg, cls=UUIDEncoder),
            properties=pika.BasicProperties(delivery_mode=2)
        )

        connection.close()

    except Exception as e:
        print(f"Failed to publish event: {e}")