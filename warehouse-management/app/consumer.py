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

    print(f" [*] Warehouse Consumer processing event: {event_type} for Order: {order_id}")

    write_db: Session = SessionLocalWrite()
    read_db: Session = SessionLocalRead()
    try:
        if event_type == "OrderCreated":
            # Add to command side (Command DB)
            db_order = models.DBWarehouseOrder(
                order_id=order_id,
                status="Pending",
                items=data.get("items", [])
            )
            write_db.add(db_order)
            write_db.commit()
            print(f" [✓] Added Order {order_id} to warehouse_orders (Command)")
            
            # Add to query side (Query DB)
            db_view = models.DBWarehouseOrderView(
                order_id=order_id,
                status="Pending",
                items=data.get("items", [])
            )
            read_db.add(db_view)
            read_db.commit()
            print(f" [✓] Added Order {order_id} to warehouse_order_views (Query)")
            
        elif event_type == "OrderCancelled":
            # Remove from command side
            db_order = write_db.query(models.DBWarehouseOrder).filter(models.DBWarehouseOrder.order_id == order_id).first()
            if db_order:
                write_db.delete(db_order)
                write_db.commit()
                print(f" [✓] Removed cancelled Order {order_id} from warehouse_orders (Command)")
            
            # Remove from query side
            db_view = read_db.query(models.DBWarehouseOrderView).filter(models.DBWarehouseOrderView.order_id == order_id).first()
            if db_view:
                read_db.delete(db_view)
                read_db.commit()
                print(f" [✓] Removed cancelled Order {order_id} from warehouse_order_views (Query)")

        elif event_type == "WarehouseOrderStatusUpdated":
            # Sync status updates to query side
            db_view = read_db.query(models.DBWarehouseOrderView).filter(models.DBWarehouseOrderView.order_id == order_id).first()
            if db_view:
                db_view.status = data.get("status", "Pending")
                read_db.commit()
                print(f" [✓] Updated Order {order_id} status to {db_view.status} in warehouse_order_views (Query)")

        elif event_type == "WarehouseOrderProcessed":
            # Order is processed and deleted from command side in API; delete from query side too
            db_view = read_db.query(models.DBWarehouseOrderView).filter(models.DBWarehouseOrderView.order_id == order_id).first()
            if db_view:
                read_db.delete(db_view)
                read_db.commit()
                print(f" [✓] Removed processed Order {order_id} from warehouse_order_views (Query)")

    except Exception as e:
        write_db.rollback()
        read_db.rollback()
        print(f" [✗] Error processing event in Warehouse Consumer: {e}")
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

    # Declare a separate queue for warehouse
    queue_name = 'warehouse_service_queue'
    channel.queue_declare(queue=queue_name, durable=True)

    # Bind queue to events
    channel.queue_bind(exchange='order_events_exchange', queue=queue_name, routing_key="order.OrderCreated")
    channel.queue_bind(exchange='order_events_exchange', queue=queue_name, routing_key="order.OrderCancelled")
    channel.queue_bind(exchange='order_events_exchange', queue=queue_name, routing_key="warehouse.WarehouseOrderStatusUpdated")
    channel.queue_bind(exchange='order_events_exchange', queue=queue_name, routing_key="warehouse.WarehouseOrderProcessed")

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
