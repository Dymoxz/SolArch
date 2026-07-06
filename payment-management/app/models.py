import uuid
from typing import Optional
from pydantic import BaseModel, Field

from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from database import WriteBase, ReadBase

from enum import Enum

class PaymentMethod(str, Enum):
    ForwardPay = "ForwardPay"
    AfterPay = "AfterPay"

class DBPaymentEvent(WriteBase):
    __tablename__ = "payment_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(PG_UUID(as_uuid=True), index=True, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class DBPaymentView(ReadBase):
    __tablename__ = "payment_views"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    order_id = Column(PG_UUID(as_uuid=True), nullable=False)
    customer_id = Column(PG_UUID(as_uuid=True), nullable=False)

    amount = Column(Integer, nullable=False)
    method = Column(String, nullable=False)

    status = Column(String, nullable=False)
    invoice_number = Column(String, nullable=True)

class PaymentCreate(BaseModel):
    order_id: uuid.UUID
    customer_id: uuid.UUID
    amount: int
    method: PaymentMethod


class PaymentResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    customer_id: uuid.UUID
    amount: int
    method: str
    status: str