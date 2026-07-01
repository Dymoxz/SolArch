import os
import json
import uuid
import pika
from uuid import UUID

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:admin_password@rabbitmq:5672/")

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)

def publish_warehouse_event(event_type: str, order_id: UUID, payload: dict):
    """Publishes an event from the Warehouse service to the RabbitMQ Event Bus."""
    try:
        parameters = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Declare the exchange (matches the exchange used by order management)
        channel.exchange_declare(exchange='order_events_exchange', exchange_type='topic', durable=True)

        event_msg = {
            "event_type": event_type,
            "order_id": order_id,
            "data": payload
        }

        channel.basic_publish(
            exchange='order_events_exchange',
            routing_key=f"warehouse.{event_type}",
            body=json.dumps(event_msg, cls=UUIDEncoder),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        print(f" [✓] Published warehouse event: {event_type} for Order: {order_id}")
    except Exception as e:
        print(f"Failed to publish warehouse event: {e}")
