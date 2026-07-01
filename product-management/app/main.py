from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException, status
import pika
import json
import os

from models import ProductCreate, ProductResponse

app = FastAPI(title="Ball.com - Product Service API")

MOCK_QUERY_DB: dict[UUID, dict] = {}

MOCK_SUPPLIERS = {
    UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6"): True
}


def supplier_exists(supplier_id: UUID) -> bool:
    return supplier_id in MOCK_SUPPLIERS


def product_exists(name: str, supplier_id: UUID) -> bool:
    return any(
        p["name"] == name and p["supplier_id"] == str(supplier_id)
        for p in MOCK_QUERY_DB.values()
    )


RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost:5672/"
)


def publish_event(event: dict):
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()

        channel.exchange_declare(
            exchange="product_events_exchange",
            exchange_type="topic",
            durable=True
        )

        channel.basic_publish(
            exchange="product_events_exchange",
            routing_key="product.created",
            body=json.dumps(event),
            properties=pika.BasicProperties(delivery_mode=2)
        )

        connection.close()

    except Exception as e:
        print(f"RabbitMQ publish failed: {e}")


@app.get("/")
def root():
    return {"status": "running"}


@app.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED
)
def add_product(product: ProductCreate):

    if not supplier_exists(product.supplier_id):
        raise HTTPException(status_code=400, detail="Supplier does not exist")

    if product_exists(product.name, product.supplier_id):
        raise HTTPException(
            status_code=409,
            detail="Product already exists for this supplier"
        )

    product_id = uuid4()

    event = {
        "event_type": "SupplierProductAdded",
        "product_id": str(product_id),
        "data": {
            "supplier_id": str(product.supplier_id),
            "name": product.name,
            "price": product.price,
            "inventory": product.inventory,
            "status": "PendingApproval"
        }
    }

    publish_event(event)

    MOCK_QUERY_DB[product_id] = {
        "id": str(product_id),
        **event["data"]
    }

    return MOCK_QUERY_DB[product_id]


@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID):

    product = MOCK_QUERY_DB.get(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Not found")

    return product


@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: UUID, product: ProductCreate):

    if product_id not in MOCK_QUERY_DB:
        raise HTTPException(status_code=404, detail="Not found")

    if not supplier_exists(product.supplier_id):
        raise HTTPException(status_code=400, detail="Supplier does not exist")

    updated_product = {
        "id": str(product_id),
        "supplier_id": str(product.supplier_id),
        "name": product.name,
        "price": product.price,
        "inventory": product.inventory,
        "status": "Updated"
    }

    MOCK_QUERY_DB[product_id] = updated_product

    return updated_product


@app.get("/products")
def list_products():
    return list(MOCK_QUERY_DB.values())


@app.delete("/products/{product_id}")
def delete_product(product_id: UUID):

    if product_id not in MOCK_QUERY_DB:
        raise HTTPException(status_code=404, detail="Not found")

    deleted = MOCK_QUERY_DB.pop(product_id)

    return {
        "message": "Product deleted",
        "deleted": deleted
    }