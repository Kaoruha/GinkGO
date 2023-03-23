from ginkgo.data.models.base_model import BaseModel
from sqlalchemy import Column, String, Boolean, func, Enum, Integer, DECIMAL


class Order(BaseModel):
    __abstract__ = False
    __tablename__ = "Orders"

    CODE = Column(String(12))
    DIRECTION = Column(Enum("LONG", "SHORT"))
    TYPE = Column(Enum("MARKET", "LIMITORDER"))
    QUANTITY = Column(Integer)
    PRICE = Column(DECIMAL(10, 2))
    STATUS = Column(Enum("NEW", "SUBMITTED", "FILLED", "CANCELED"))
