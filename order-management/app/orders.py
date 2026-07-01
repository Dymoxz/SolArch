from pydantic import BaseModel, Field
from typing import List
from uuid import UUID, uuid4

class OrderItem(BaseModel):
    product_id: UUID
    quantity: int = Field(..., ge=1, le=20, description="Amount of said productId")

class OrderCreate(BaseModel):
    customer_id: UUID
    items: List[OrderItem]

class OrderResponse(BaseModel):
    id: UUID
    customer_id: UUID
    items: List[OrderItem]
    status: str