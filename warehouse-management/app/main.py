from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

import models
from database import engine, get_db
from messaging import publish_warehouse_event

# Ensure tables are created
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ball.com - Warehouse Management API")

@app.get("/warehouse/orders", response_model=list[models.WarehouseOrderResponse])
def get_warehouse_orders(db: Session = Depends(get_db)):
    """Retrieve all pending orders in the warehouse."""
    return db.query(models.DBWarehouseOrder).all()

@app.get("/warehouse/orders/{order_id}", response_model=models.WarehouseOrderResponse)
def get_warehouse_order(order_id: UUID, db: Session = Depends(get_db)):
    """Retrieve details of a specific warehouse order."""
    warehouse_order = db.query(models.DBWarehouseOrder).filter(models.DBWarehouseOrder.order_id == order_id).first()
    if not warehouse_order:
        raise HTTPException(status_code=404, detail="Order not found in warehouse")
    return warehouse_order

@app.put("/warehouse/orders/{order_id}/status")
def update_order_status(order_id: UUID, status: str, db: Session = Depends(get_db)):
    """Update the status of a warehouse order.
    
    If the status is updated to 'Processed', it will:
    1. Publish a 'WarehouseOrderProcessed' event.
    2. Remove the order from the warehouse_orders table (since it is completed).
    """
    warehouse_order = db.query(models.DBWarehouseOrder).filter(models.DBWarehouseOrder.order_id == order_id).first()
    if not warehouse_order:
        raise HTTPException(status_code=404, detail="Order not found in warehouse")

    valid_statuses = ["Pending", "Packing", "Processed"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of {valid_statuses}"
        )

    if status == "Processed":
        # 1. Publish the event to notify Order Management
        event_payload = {
            "order_id": str(order_id),
            "status": "Processed"
        }
        publish_warehouse_event("WarehouseOrderProcessed", order_id, event_payload)
        
        # 2. Remove the order from warehouse table
        db.delete(warehouse_order)
        db.commit()
        return {"message": "Order processed successfully, removed from warehouse inventory, and notified Order Management."}
    
    else:
        warehouse_order.status = status
        db.commit()
        db.refresh(warehouse_order)
        return warehouse_order
