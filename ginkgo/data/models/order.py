from ginkgo.data.models.base_model import BaseModel
from ginkgo.enums import OrderType, OrderStatus
from sqlalchemy import Column, String, Boolean, func, Enum, Integer, DECIMAL


class Order(BaseModel):
    __abstract__ = False
    __tablename__ = "Orders"

    CODE = Column(String(12), default="default")
    # DIRECTION = Column(Enum(OrderType))
    # TYPE = Column(Enum("MARKET", "LIMITORDER"))
    # QUANTITY = Column(Integer)
    # PRICE = Column(DECIMAL(10, 2))
    # STATUS = Column(Enum("NEW", "SUBMITTED", "FILLED", "CANCELED"))
