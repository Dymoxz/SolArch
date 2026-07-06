from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from database import write_engine, read_engine, get_write_db, get_read_db
from messaging import publish_warehouse_event

# Ensure tables are created in their respective databases
models.WriteBase.metadata.create_all(bind=write_engine)
models.ReadBase.metadata.create_all(bind=read_engine)

app = FastAPI(title="Ball.com - Warehouse Management API")

@app.get("/warehouse/orders", response_model=list[models.WarehouseOrderResponse])
def get_warehouse_orders(read_db: Session = Depends(get_read_db)):
    """Retrieve all pending orders in the warehouse."""
    return read_db.query(models.DBWarehouseOrderView).all()

@app.get("/warehouse/orders/{order_id}", response_model=models.WarehouseOrderResponse)
def get_warehouse_order(order_id: UUID, read_db: Session = Depends(get_read_db)):
    """Retrieve details of a specific warehouse order."""
    warehouse_order = read_db.query(models.DBWarehouseOrderView).filter(models.DBWarehouseOrderView.order_id == order_id).first()
    if not warehouse_order:
        raise HTTPException(status_code=404, detail="Order not found in warehouse read view")
    return warehouse_order

@app.put("/warehouse/orders/{order_id}/status")
def update_order_status(order_id: UUID, status: str, write_db: Session = Depends(get_write_db)):
    """Update the status of a warehouse order.
    
    If the status is updated to 'Processed', it will:
    1. Publish a 'WarehouseOrderProcessed' event.
    2. Remove the order from the warehouse_orders table in Command DB.
    """
    warehouse_order = write_db.query(models.DBWarehouseOrder).filter(models.DBWarehouseOrder.order_id == order_id).first()
    if not warehouse_order:
        raise HTTPException(status_code=404, detail="Order not found in warehouse command DB")

    valid_statuses = ["Pending", "Packing", "Processed"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of {valid_statuses}"
        )

    if status == "Processed":
        # 1. Publish the event to notify Order Management and delete the read view
        event_payload = {
            "order_id": str(order_id),
            "status": "Processed"
        }
        publish_warehouse_event("WarehouseOrderProcessed", order_id, event_payload)
        
        # 2. Remove the order from warehouse table
        write_db.delete(warehouse_order)
        write_db.commit()
        return {"message": "Order processed successfully, removed from warehouse inventory, and notified Order Management."}
    
    else:
        warehouse_order.status = status
        write_db.commit()
        
        # Publish status update event so the consumer updates the Read DB view
        event_payload = {
            "order_id": str(order_id),
            "status": status
        }
        publish_warehouse_event("WarehouseOrderStatusUpdated", order_id, event_payload)
        
        return {
            "order_id": warehouse_order.order_id,
            "status": warehouse_order.status,
            "items": warehouse_order.items
        }
