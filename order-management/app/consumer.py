import os
import sys
import json
import pika
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from messaging import publish_order_event

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:admin_password@rabbitmq:5672/")


def process_event(event_msg: dict):
    event_type = event_msg.get("event_type")
    order_id = event_msg.get("order_id")
    data = event_msg.get("data", {})

    print(f" [*] Processing event: {event_type} for Order: {order_id}")

    db: Session = SessionLocal()
    try:
        if event_type == "OrderCreated":
            db_view = models.DBOrderView(
                id=order_id,
                customer_id=data["customer_id"],
                status=data["status"],
                items=data["items"]
            )
            db.add(db_view)
            db.commit()
            print(f" [✓] Created Read View for Order {order_id}")

        elif event_type == "OrderCancelled":
            db_view = db.query(models.DBOrderView).filter(models.DBOrderView.id == order_id).first()
            if db_view:
                db.delete(db_view)
                db.commit()
                print(f" [✓] Deleted Read View for Order {order_id}")

        elif event_type == "WarehouseOrderProcessed":
            # 1. Append a Processed Event to the Event Store (Write Side)
            db_event = models.DBOrderEvent(
                order_id=order_id,
                event_type="OrderProcessed",
                payload=data
            )
            db.add(db_event)
            db.commit()
            print(f" [✓] Appended OrderProcessed event for Order {order_id}")

            # 2. Update status in Read View
            db_view = db.query(models.DBOrderView).filter(models.DBOrderView.id == order_id).first()
            if db_view:
                db_view.status = "Processed"
                db.commit()
                print(f" [✓] Updated Read View status for Order {order_id} to Processed")

                # 3. Publish order to Shipping Management
                shipping_payload = {
                    "customer_id": str(db_view.customer_id),
                    "items": db_view.items
                }
                publish_order_event("OrderSentToShipping", order_id, shipping_payload)
                print(f" [✓] Published OrderSentToShipping event for Order {order_id}")

    except Exception as e:
        db.rollback()
        print(f" [✗] Error processing event: {e}")
    finally:
        db.close()


def main():
    parameters = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.exchange_declare(exchange='order_events_exchange', exchange_type='topic', durable=True)

    queue_name = 'order_query_service_queue'
    channel.queue_declare(queue=queue_name, durable=True)

    channel.queue_bind(exchange='order_events_exchange', queue=queue_name, routing_key="order.*")
    channel.queue_bind(exchange='order_events_exchange', queue=queue_name, routing_key="warehouse.*")

    def callback(ch, method, properties, body):
        try:
            event_msg = json.loads(body.decode())
            process_event(event_msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as err:
            print(f"Failed to process message payload: {err}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    print(' [*] Waiting for Order Events. To exit press CTRL+C')
    channel.start_consuming()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)