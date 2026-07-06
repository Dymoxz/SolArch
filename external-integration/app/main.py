import os

import pika
import json
import pandas as pd


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:admin_password@rabbitmq:5672/")


def ingest_excel_to_bus():
    # Connect to your existing RabbitMQ container
    parameters = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    # Declare a Topic exchange
    channel.exchange_declare(exchange='excel_data_exchange', exchange_type='topic', durable=True)

    df = pd.read_excel('external_source.xlsx')

    for index, row in df.iterrows():
        payload = row.to_dict()
        for key, value in payload.items():
            if isinstance(value, pd.Timestamp):
                payload[key] = value.isoformat()
                
        if isinstance(payload.get('responses'), str):
            try:
                payload['responses'] = json.loads(payload['responses'])
            except ValueError:
                payload['responses'] = []


        routing_key = f"excel.{row['type']}.sync"

        channel.basic_publish(
            exchange='excel_data_exchange',
            routing_key=routing_key,
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2)  # Persistent
        )
        print(f"Sent ticket to bus under key [{routing_key}] for user: {row['user_id']}")

    connection.close()

if __name__ == "__main__":
    ingest_excel_to_bus()