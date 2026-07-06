import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_WRITE_URL = os.getenv(
    "DATABASE_WRITE_URL",
    "postgresql://command_user:command_password@db-command:5432/command_db"
)
DATABASE_READ_URL = os.getenv(
    "DATABASE_READ_URL",
    "postgresql://query_user:query_password@db-query:5432/query_db"
)

write_engine = create_engine(DATABASE_WRITE_URL)
read_engine = create_engine(DATABASE_READ_URL)

SessionLocalWrite = sessionmaker(autocommit=False, autoflush=False, bind=write_engine)
SessionLocalRead = sessionmaker(autocommit=False, autoflush=False, bind=read_engine)

WriteBase = declarative_base()
ReadBase = declarative_base()

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
