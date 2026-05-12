from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from scanner import run_scanner
import scheduler
from database import engine, SessionLocal
from models import Base, Alert

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Options Flow Screener API"
    }


@app.get("/scan")
def scan_market(
    price_trigger: float = Query(2.0, ge=0),
    spread_trigger: float = Query(0.5, ge=0),
    atm_trigger: float = Query(4.0, ge=0),
):
    return run_scanner(
        price_trigger=price_trigger,
        spread_trigger=spread_trigger,
        atm_trigger=atm_trigger,
    )


@app.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).all()
    return alerts
