import uuid
from database import WriteBase, ReadBase
from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

class DBShipment(WriteBase):
    """Shipment record, representing orders forwarded to Shipping Management."""

    __tablename__ = "shipments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String, nullable=False, default="ReadyForShipping")  # e.g., ReadyForShipping, Shipped
    created_at = Column(DateTime, server_default=func.now())

class DBShipmentView(ReadBase):
    """Query Side: Materialized read view of shipment records for fast GET requests."""

    __tablename__ = "shipment_views"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    order_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)

class ShipmentResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str

    class Config:
        from_attributes = True
