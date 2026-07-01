import os
import sys
import json
import pika
from sqlalchemy.orm import Session

import models
from database import SessionLocal, engine

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:admin_password@rabbitmq:5672/")

def process_event(event_msg: dict):
    event_type = event_msg.get("event_type")
    order_id = event_msg.get("order_id")
    data = event_msg.get("data", {})

    print(f" [*] Warehouse Consumer processing event: {event_type} for Order: {order_id}")

    db: Session = SessionLocal()
    try:
        if event_type == "OrderCreated":
            # Add to warehouse orders table with status "Pending"
            db_order = models.DBWarehouseOrder(
                order_id=order_id,
                status="Pending",
                items=data.get("items", [])
            )
            db.add(db_order)
            db.commit()
            print(f" [✓] Added Order {order_id} to warehouse_orders")
            
        elif event_type == "OrderCancelled":
            # If order cancelled, remove it from warehouse
            db_order = db.query(models.DBWarehouseOrder).filter(models.DBWarehouseOrder.order_id == order_id).first()
            if db_order:
                db.delete(db_order)
                db.commit()
                print(f" [✓] Removed cancelled Order {order_id} from warehouse_orders")

    except Exception as e:
        db.rollback()
        print(f" [✗] Error processing event in Warehouse Consumer: {e}")
    finally:
        db.close()

def main():
    # Make sure tables exist
    models.Base.metadata.create_all(bind=engine)
    
    parameters = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    # Declare exchange
    channel.exchange_declare(exchange='order_events_exchange', exchange_type='topic', durable=True)

    # Declare a separate queue for warehouse
    queue_name = 'warehouse_service_queue'
    channel.queue_declare(queue=queue_name, durable=True)

    # Bind queue to OrderCreated and OrderCancelled events
    channel.queue_bind(exchange='order_events_exchange', queue=queue_name, routing_key="order.OrderCreated")
    channel.queue_bind(exchange='order_events_exchange', queue=queue_name, routing_key="order.OrderCancelled")

    def callback(ch, method, properties, body):
        try:
            event_msg = json.loads(body.decode())
            process_event(event_msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as err:
            print(f"Failed to process message payload in Warehouse: {err}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    print(' [*] Warehouse Consumer waiting for events. To exit press CTRL+C')
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
