import os
import json
import uuid

import pika
from uuid import UUID

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

# 1. Add a custom encoder that handles UUID objects automatically
class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)
def publish_order_event(event_type: str, order_id: UUID, payload: dict):
    """Publishes an event to the RabbitMQ Event Bus to notify the Query DB."""
    try:
        parameters = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Declare an exchange for Order Events
        channel.exchange_declare(exchange='order_events_exchange', exchange_type='topic', durable=True)

        event_msg = {
            "event_type": event_type,
            "order_id": order_id,
            "data": payload
        }

        channel.basic_publish(
            exchange='order_events_exchange',
            routing_key=f"order.{event_type}",
            body=json.dumps(event_msg, cls=UUIDEncoder),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
    except Exception as e:
        print(f"Failed to publish event: {e}")
        # In production, handle this gracefully (outbox pattern)