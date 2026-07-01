import uuid
from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from database import Base

class DBProductView(Base):
    __tablename__ = "product_views"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    supplier_id = Column(PG_UUID(as_uuid=True), nullable=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    inventory = Column(Integer, nullable=False)
    status = Column(String, nullable=False)

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    is_trusted = Column(Boolean, default=True)

class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    supplier_id = Column(PG_UUID(as_uuid=True), ForeignKey("suppliers.id"))
    product_name = Column(String)
    price = Column(Integer)
    approved = Column(String, default="Pending")


class ProductCreate(BaseModel):
    name: str
    price: int
    inventory: int
    supplier_id: uuid.UUID


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    price: int
    inventory: int
    status: str