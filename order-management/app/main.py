import os
from typing import List
from uuid import UUID, uuid4
import pika
from fastapi import FastAPI, HTTPException, status


from orders import OrderItem, OrderCreate, OrderResponse
from messaging import publish_order_event

app = FastAPI(title="Ball.com - Order Management API")

# Mock In-Memory Databases to separate concerns
MOCK_EVENT_STORE = {}  # Write Side
MOCK_QUERY_DB = {}  # Read Side (Populated asynchronously via Event Bus in real life)


@app.get("/")
def read_root():
    return {"message": "Order Management API is online!"}


@app.get("/health/rabbitmq")
def check_rabbitmq():
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    try:
        parameters = pika.URLParameters(rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        connection.close()
        return {"status": "RabbitMQ is verbonden"}
    except Exception as e:
        return {"status": "Kan geen verbinding maken met RabbitMQ", "error": str(e)}


# --- COMMAND SIDE (POST, PUT, DELETE) ---

@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order_data: OrderCreate):
    # Business Rule: 1 to 20 items total in the order
    total_items = sum(item.quantity for item in order_data.items)
    if not (1 <= total_items <= 20):
        raise HTTPException(status_code=400, detail="An order must contain between 1 and 20 items total.")

    order_id = uuid4()

    # 1. Save to Event Store (Command side)
    event_payload = {
        "customer_id": str(order_data.customer_id),
        "items": [item.model_dump() for item in order_data.items],
        "status": "Created"
    }
    MOCK_EVENT_STORE[order_id] = [{"event_type": "OrderCreated", "data": event_payload}]

    # 2. Publish to Event Bus (RabbitMQ)
    publish_order_event("OrderCreated", order_id, event_payload)

    # For demo purposes, we eagerly write to the Query DB so GET works immediately
    MOCK_QUERY_DB[order_id] = {**event_payload, "id": order_id}

    return MOCK_QUERY_DB[order_id]


@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: UUID, order_data: OrderCreate):
    if order_id not in MOCK_QUERY_DB:
        raise HTTPException(status_code=404, detail="Order not found")

    event_payload = {
        "items": [item.model_dump() for item in order_data.items]
    }

    # Append event to store
    MOCK_EVENT_STORE[order_id].append({"event_type": "OrderUpdated", "data": event_payload})

    # Publish update event
    publish_order_event("OrderUpdated", order_id, event_payload)

    # Update read side
    MOCK_QUERY_DB[order_id]["items"] = order_data.items
    return MOCK_QUERY_DB[order_id]


@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: UUID):
    if order_id not in MOCK_QUERY_DB:
        raise HTTPException(status_code=404, detail="Order not found")

    # Append Cancelled event to store
    MOCK_EVENT_STORE[order_id].append({"event_type": "OrderCancelled", "data": {}})

    # Publish cancellation
    publish_order_event("OrderCancelled", order_id, {})

    # Remove from query view
    del MOCK_QUERY_DB[order_id]
    return


# --- QUERY SIDE (GET) ---

@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: UUID):
    """
    Fetches the order view from the Read/Query Database (Materialized view).
    """
    order = MOCK_QUERY_DB.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found in Query DB")
    return order