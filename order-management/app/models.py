import uuid
from typing import List

from database import Base
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship


class DBOrderEvent(Base):
    """The Command Side: Event Store tracking every state change."""

    __tablename__ = "order_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # e.g., OrderCreated, OrderCancelled
    payload = Column(JSONB, nullable=False)  # Event data payload
    created_at = Column(DateTime, server_default=func.now())


class DBOrderView(Base):
    """The Query Side: Materialized view optimized for fast GET requests."""

    __tablename__ = "order_views"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    customer_id = Column(PG_UUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=False)
    items = Column(JSONB, nullable=False)


class OrderItem(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(..., ge=1, le=20, description="Amount of said productId")


class OrderCreate(BaseModel):
    customer_id: uuid.UUID
    items: List[OrderItem]


class OrderResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    items: List[OrderItem]
    status: str
