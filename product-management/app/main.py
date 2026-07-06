from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException, status
import pika
import json
import os

from models import ProductCreate, ProductResponse

from database import write_engine, read_engine, get_write_db, get_read_db
from sqlalchemy.orm import Session
from fastapi import Depends
import models

# Ensure tables are created in their respective databases
models.WriteBase.metadata.create_all(bind=write_engine)
models.ReadBase.metadata.create_all(bind=read_engine)

# Seed default supplier on startup
from database import SessionLocalWrite
db = SessionLocalWrite()
try:
    default_supplier_id = UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")
    exists = db.query(models.Supplier).filter(models.Supplier.id == default_supplier_id).first()
    if not exists:
        supplier = models.Supplier(id=default_supplier_id, name="Default Supplier", is_trusted=True)
        db.add(supplier)
        db.commit()
finally:
    db.close()

app = FastAPI(title="Ball.com - Product Service API")


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
def add_product(product: ProductCreate, write_db: Session = Depends(get_write_db), read_db: Session = Depends(get_read_db)):

    supplier = write_db.query(models.Supplier).filter(models.Supplier.id == product.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=400, detail="Supplier does not exist")

    exists = read_db.query(models.DBProductView).filter(
        models.DBProductView.name == product.name,
        models.DBProductView.supplier_id == product.supplier_id
    ).first()
    if exists:
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

    # Insert into the query view directly to ensure it is immediately available
    db_view = models.DBProductView(
        id=product_id,
        supplier_id=product.supplier_id,
        name=product.name,
        price=product.price,
        inventory=product.inventory,
        status="PendingApproval"
    )
    read_db.add(db_view)
    read_db.commit()

    return db_view


@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID, read_db: Session = Depends(get_read_db)):

    product = read_db.query(models.DBProductView).filter(models.DBProductView.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Not found")

    return product


@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: UUID, product: ProductCreate, write_db: Session = Depends(get_write_db), read_db: Session = Depends(get_read_db)):

    supplier = write_db.query(models.Supplier).filter(models.Supplier.id == product.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=400, detail="Supplier does not exist")

    db_product = read_db.query(models.DBProductView).filter(models.DBProductView.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Not found")

    db_product.supplier_id = product.supplier_id
    db_product.name = product.name
    db_product.price = product.price
    db_product.inventory = product.inventory
    db_product.status = "Updated"
    read_db.commit()

    return db_product


@app.get("/products")
def list_products(read_db: Session = Depends(get_read_db)):
    return read_db.query(models.DBProductView).all()


@app.get("/products/list")
def list_products_alt(read_db: Session = Depends(get_read_db)):
    return read_db.query(models.DBProductView).all()


@app.delete("/products/{product_id}")
def delete_product(product_id: UUID, read_db: Session = Depends(get_read_db)):

    product = read_db.query(models.DBProductView).filter(models.DBProductView.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Not found")

    read_db.delete(product)
    read_db.commit()

    return {
        "message": "Product deleted",
        "deleted": {
            "id": str(product.id),
            "name": product.name,
            "price": product.price,
            "inventory": product.inventory,
            "status": product.status
        }
    }