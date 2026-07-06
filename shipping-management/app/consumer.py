import os
import sys
import json
import pika
from sqlalchemy.orm import Session

import models
from database import SessionLocalWrite, SessionLocalRead, write_engine, read_engine

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:admin_password@rabbitmq:5672/")

def process_event(event_msg: dict):
    event_type = event_msg.get("event_type")
    order_id = event_msg.get("order_id")
    data = event_msg.get("data", {})

    print(f" [*] Shipping Consumer processing event: {event_type} for Order: {order_id}")

    write_db: Session = SessionLocalWrite()
    read_db: Session = SessionLocalRead()
    try:
        if event_type == "OrderSentToShipping":
            # Create a new shipment on command side (Command DB)
            db_shipment = models.DBShipment(
                order_id=order_id,
                status="ReadyForShipping"
            )
            write_db.add(db_shipment)
            write_db.commit()
            print(f" [✓] Created shipment for Order {order_id} in shipments (Command)")

            # Create a new shipment on query side (Query DB)
            db_view = models.DBShipmentView(
                id=db_shipment.id,
                order_id=order_id,
                status="ReadyForShipping",
                created_at=db_shipment.created_at
            )
            read_db.add(db_view)
            read_db.commit()
            print(f" [✓] Created shipment for Order {order_id} in shipment_views (Query)")

    except Exception as e:
        write_db.rollback()
        read_db.rollback()
        print(f" [✗] Error processing event in Shipping Consumer: {e}")
    finally:
        write_db.close()
        read_db.close()

def main():
    # Make sure tables exist
    models.WriteBase.metadata.create_all(bind=write_engine)
    models.ReadBase.metadata.create_all(bind=read_engine)
    
    parameters = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    # Declare exchange
    channel.exchange_declare(exchange='order_events_exchange', exchange_type='topic', durable=True)

    # Declare a separate queue for shipping
    queue_name = 'shipping_service_queue'
    channel.queue_declare(queue=queue_name, durable=True)

    # Bind queue to OrderSentToShipping events
    channel.queue_bind(exchange='order_events_exchange', queue=queue_name, routing_key="order.OrderSentToShipping")

    def callback(ch, method, properties, body):
        try:
            event_msg = json.loads(body.decode())
            process_event(event_msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as err:
            print(f"Failed to process message payload in Shipping: {err}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    print(' [*] Shipping Consumer waiting for events. To exit press CTRL+C')
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
