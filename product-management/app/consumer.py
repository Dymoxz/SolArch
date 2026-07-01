import json
import pika
import os
from uuid import UUID
from sqlalchemy.orm import Session

from database import SessionLocal
import models

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost:5672/"
)


def process_event(event_msg: dict):
    event_type = event_msg.get("event_type")
    product_id = UUID(event_msg.get("product_id"))
    data = event_msg.get("data", {})

    print(f"[*] Processing event: {event_type} for Product: {product_id}")

    db: Session = SessionLocal()

    try:

        if event_type == "SupplierProductAdded":
            existing = db.query(models.DBProductView)\
                .filter(models.DBProductView.id == product_id)\
                .first()

            if existing:
                print(f"[=] Product already exists, skipping insert {product_id}")
            else:
                db_view = models.DBProductView(
                    id=product_id,
                    supplier_id=data["supplier_id"],
                    name=data["name"],
                    price=data["price"],
                    inventory=data["inventory"],
                    status=data["status"]
                )
                db.add(db_view)
                print(f"[+] Created Product View {product_id}")

            db.commit()

        elif event_type == "SupplierProductApproved":

            db_view = db.query(models.DBProductView)\
                .filter(models.DBProductView.id == product_id).first()

            if db_view:
                db_view.status = "Approved"
                db.commit()
                print(f"[✓] Approved Product {product_id}")

        elif event_type == "SupplierProductRejected":

            db_view = db.query(models.DBProductView)\
                .filter(models.DBProductView.id == product_id).first()

            if db_view:
                db_view.status = "Rejected"
                db.commit()
                print(f"[✓] Rejected Product {product_id}")

        elif event_type == "InventoryUpdated":

            db_view = db.query(models.DBProductView)\
                .filter(models.DBProductView.id == product_id).first()

            if db_view:
                db_view.inventory = data["inventory"]
                db.commit()
                print(f"[✓] Inventory updated for {product_id}")

    except Exception as e:
        db.rollback()
        print(f"[✗] Error processing event: {e}")

    finally:
        db.close()


def main():

    parameters = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    channel.exchange_declare(
        exchange='product_events_exchange',
        exchange_type='topic',
        durable=True
    )

    queue_name = 'product_query_service_queue'

    channel.queue_declare(queue=queue_name, durable=True)

    channel.queue_bind(
        exchange='product_events_exchange',
        queue=queue_name,
        routing_key="product.*"
    )

    def callback(ch, method, properties, body):
        try:
            event_msg = json.loads(body.decode())

            process_event(event_msg)

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as err:
            print(f"Failed to process message: {err}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    print("[*] Waiting for Product Events...")
    channel.start_consuming()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")