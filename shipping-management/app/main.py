from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

import models
from database import write_engine, read_engine, get_write_db, get_read_db

# Ensure tables are created in their respective databases
models.WriteBase.metadata.create_all(bind=write_engine)
models.ReadBase.metadata.create_all(bind=read_engine)

app = FastAPI(title="Ball.com - Shipping Management API")

@app.get("/shipping/shipments", response_model=list[models.ShipmentResponse])
def get_shipments(read_db: Session = Depends(get_read_db)):
    """Retrieve all shipments."""
    return read_db.query(models.DBShipmentView).all()
