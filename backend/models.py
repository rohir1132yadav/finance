from sqlalchemy import Column, Integer, String, Float
from database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    stock = Column(String)
    price = Column(Float)
    change_percent = Column(Float)
    spread = Column(Float)
    liquidity = Column(Float)
    atm_premium = Column(Float)
    atm = Column(Float)
    signal = Column(String)