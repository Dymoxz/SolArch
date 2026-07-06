import uuid
from typing import List
from database import WriteBase, ReadBase
from pydantic import BaseModel
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

class DBWarehouseOrder(WriteBase):
    """Warehouse order storage. Stores orders that are created but not yet completed."""

    __tablename__ = "warehouse_orders"

    order_id = Column(PG_UUID(as_uuid=True), primary_key=True)
    status = Column(String, nullable=False, default="Pending")  # e.g., Pending, Packing, Processed
    items = Column(JSONB, nullable=False)  # List of items in the order

class DBWarehouseOrderView(ReadBase):
    """Query Side: Materialized view of warehouse orders for fast GET requests."""

    __tablename__ = "warehouse_order_views"

    order_id = Column(PG_UUID(as_uuid=True), primary_key=True)
    status = Column(String, nullable=False)
    items = Column(JSONB, nullable=False)

class OrderItem(BaseModel):
    product_id: uuid.UUID
    quantity: int

class WarehouseOrderResponse(BaseModel):
    order_id: uuid.UUID
    status: str
    items: List[OrderItem]

    class Config:
        from_attributes = True
