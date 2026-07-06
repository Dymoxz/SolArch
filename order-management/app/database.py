import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database URLs matching our segregated CQRS architecture
DATABASE_WRITE_URL = os.getenv(
    "DATABASE_WRITE_URL",
    "postgresql://order_user:order_password@db-order-write:5432/order_write"
)
DATABASE_READ_URL = os.getenv(
    "DATABASE_READ_URL",
    "postgresql://order_user:order_password@db-order-read:5432/order_read"
)

write_engine = create_engine(DATABASE_WRITE_URL)
read_engine = create_engine(DATABASE_READ_URL)

SessionLocalWrite = sessionmaker(autocommit=False, autoflush=False, bind=write_engine)
SessionLocalRead = sessionmaker(autocommit=False, autoflush=False, bind=read_engine)

WriteBase = declarative_base()
ReadBase = declarative_base()

# Dependencies to yield database sessions to FastAPI routes
def get_write_db():
    db = SessionLocalWrite()
    try:
        yield db
    finally:
        db.close()

def get_read_db():
    db = SessionLocalRead()
    try:
        yield db
    finally:
        db.close()