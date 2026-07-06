import os
from typing import List
from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException, status, Depends
from sqlalchemy.orm import Session

import models
from database import write_engine, read_engine, get_write_db, get_read_db
from messaging import publish_order_event

# Create the database tables in their respective databases
models.WriteBase.metadata.create_all(bind=write_engine)
models.ReadBase.metadata.create_all(bind=read_engine)

app = FastAPI(title="Ball.com - Order Management API")


@app.post("/orders", response_model=models.OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order_data: models.OrderCreate, write_db: Session = Depends(get_write_db)):
    total_items = sum(item.quantity for item in order_data.items)
    if not (1 <= total_items <= 20):
        raise HTTPException(status_code=400, detail="An order must contain between 1 and 20 items total.")

    order_id = uuid4()
    serialized_items = [item.model_dump() for item in order_data.items]

    for item in serialized_items:
        item["product_id"] = str(item["product_id"])

    event_payload = {
        "customer_id": str(order_data.customer_id),
        "status": "Created",
        "items": serialized_items
    }
    db_event = models.DBOrderEvent(
        order_id=order_id,
        event_type="OrderCreated",
        payload=event_payload
    )
    write_db.add(db_event)
    write_db.commit()

    publish_order_event("OrderCreated", order_id, event_payload)

    return {
        "id": order_id,
        "customer_id": order_data.customer_id,
        "status": "Created",
        "items": order_data.items
    }


@app.get("/orders", response_model=List[models.OrderResponse])
def get_orders(read_db: Session = Depends(get_read_db)):
    return read_db.query(models.DBOrderView).all()


@app.get("/orders/{order_id}", response_model=models.OrderResponse)
def get_order(order_id: UUID, read_db: Session = Depends(get_read_db)):
    order_view = read_db.query(models.DBOrderView).filter(models.DBOrderView.id == order_id).first()
    if not order_view:
        raise HTTPException(status_code=404, detail="Order not found in Read View")
    return order_view


@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: UUID, write_db: Session = Depends(get_write_db)):
    exists = write_db.query(models.DBOrderEvent).filter(models.DBOrderEvent.order_id == order_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Order not found")

    # 1. Append a Cancellation Event to the Event Store (Write Side)
    db_event = models.DBOrderEvent(
        order_id=order_id,
        event_type="OrderCancelled",
        payload={}
    )
    write_db.add(db_event)
    write_db.commit()

    # 3. Publish cancellation notice to Event Bus
    publish_order_event("OrderCancelled", order_id, {})
    return