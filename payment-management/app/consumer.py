import os
import json
import pika
from uuid import UUID
from sqlalchemy.orm import Session

import models
from database import SessionLocal

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://admin:admin_password@rabbitmq:5672/"
)


def process_event(event_msg: dict):

    event_type = event_msg.get("event_type")
    payment_id = UUID(event_msg.get("payment_id"))
    data = event_msg.get("data", {})

    db: Session = SessionLocal()

    try:

        if event_type == "PaymentInitiated":

            db_view = models.DBPaymentView(
                id=payment_id,
                order_id=data["order_id"],
                customer_id=data["customer_id"],
                amount=data["amount"],
                method=data["method"],
                status="Initiated"
            )

            db.add(db_view)
            db.commit()

        elif event_type == "PaymentAuthorized":

            payment = db.query(models.DBPaymentView)\
                .filter(models.DBPaymentView.id == payment_id)\
                .first()

            if payment:
                payment.status = "Authorized"
                db.commit()

        elif event_type == "PaymentCaptured":

            payment = db.query(models.DBPaymentView)\
                .filter(models.DBPaymentView.id == payment_id)\
                .first()

            if payment:
                payment.status = "Captured"
                db.commit()

        elif event_type == "PaymentFailed":

            payment = db.query(models.DBPaymentView)\
                .filter(models.DBPaymentView.id == payment_id)\
                .first()

            if payment:
                payment.status = "Failed"
                db.commit()

        elif event_type == "InvoiceGenerated":

            payment = db.query(models.DBPaymentView)\
                .filter(models.DBPaymentView.id == payment_id)\
                .first()

            if payment:
                payment.invoice_number = data["invoice_number"]
                db.commit()

    finally:
        db.close()


def main():

    connection = pika.BlockingConnection(
        pika.URLParameters(RABBITMQ_URL)
    )

    channel = connection.channel()

    channel.exchange_declare(
        exchange="payment_events_exchange",
        exchange_type="topic",
        durable=True
    )

    queue_name = "payment_query_service_queue"

    channel.queue_declare(queue=queue_name, durable=True)

    channel.queue_bind(
        exchange="payment_events_exchange",
        queue=queue_name,
        routing_key="payment.*"
    )

    def callback(ch, method, properties, body):
        try:
            event_msg = json.loads(body.decode())
            process_event(event_msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Error: {e}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    print("[*] Payment Consumer running...")
    channel.start_consuming()


if __name__ == "__main__":
    main()