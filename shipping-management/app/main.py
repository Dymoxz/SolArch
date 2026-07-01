from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

import models
from database import engine, get_db

# Ensure tables are created
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ball.com - Shipping Management API")

@app.get("/shipping/shipments", response_model=list[models.ShipmentResponse])
def get_shipments(db: Session = Depends(get_db)):
    """Retrieve all shipments."""
    return db.query(models.DBShipment).all()
