from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

import models
from database import write_engine, read_engine, get_write_db, get_read_db
from messaging import publish_payment_event

models.WriteBase.metadata.create_all(bind=write_engine)
models.ReadBase.metadata.create_all(bind=read_engine)

app = FastAPI(title="Ball.com - Payment Service API")


@app.post("/payments", response_model=models.PaymentResponse)
def create_payment(payment: models.PaymentCreate, write_db: Session = Depends(get_write_db), read_db: Session = Depends(get_read_db)):

    existing = read_db.query(models.DBPaymentView)\
        .filter(models.DBPaymentView.order_id == payment.order_id)\
        .first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="A payment already exists for this order."
        )

    payment_id = uuid4()

    payload = {
        "order_id": str(payment.order_id),
        "customer_id": str(payment.customer_id),
        "amount": payment.amount,
        "method": payment.method,
        "status": "Initiated"
    }

    db_event = models.DBPaymentEvent(
        payment_id=payment_id,
        event_type="PaymentInitiated",
        payload=payload
    )

    write_db.add(db_event)
    write_db.commit()

    publish_payment_event("PaymentInitiated", payment_id, payload)

    return {
        "id": payment_id,
        **payload
    }


@app.get("/payments", response_model=list[models.PaymentResponse])
def get_all_payments(read_db: Session = Depends(get_read_db)):
    return read_db.query(models.DBPaymentView).all()


@app.get("/payments/{payment_id}", response_model=models.PaymentResponse)
def get_payment(payment_id, read_db: Session = Depends(get_read_db)):

    payment = read_db.query(models.DBPaymentView)\
        .filter(models.DBPaymentView.id == payment_id)\
        .first()

    if not payment:
        raise HTTPException(status_code=404, detail="Not found")

    return payment


@app.put("/payments/{payment_id}", response_model=models.PaymentResponse)
def update_payment(payment_id, payment: models.PaymentCreate, read_db: Session = Depends(get_read_db)):

    db_payment = read_db.query(models.DBPaymentView)\
        .filter(models.DBPaymentView.id == payment_id)\
        .first()

    if not db_payment:
        raise HTTPException(status_code=404, detail="Not found")

    existing = read_db.query(models.DBPaymentView)\
        .filter(models.DBPaymentView.order_id == payment.order_id)\
        .filter(models.DBPaymentView.id != payment_id)\
        .first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Another payment already exists for this order."
        )

    db_payment.order_id = payment.order_id
    db_payment.customer_id = payment.customer_id
    db_payment.amount = payment.amount
    db_payment.method = payment.method

    read_db.commit()

    payload = {
        "order_id": str(payment.order_id),
        "customer_id": str(payment.customer_id),
        "amount": payment.amount,
        "method": payment.method,
        "status": db_payment.status
    }

    publish_payment_event("PaymentUpdated", payment_id, payload)

    return db_payment


@app.delete("/payments/{payment_id}")
def delete_payment(payment_id, read_db: Session = Depends(get_read_db)):

    payment = read_db.query(models.DBPaymentView)\
        .filter(models.DBPaymentView.id == payment_id)\
        .first()

    if not payment:
        raise HTTPException(status_code=404, detail="Not found")

    read_db.delete(payment)
    read_db.commit()

    publish_payment_event("PaymentDeleted", payment_id, {})

    return {"message": "Payment deleted", "id": str(payment_id)}