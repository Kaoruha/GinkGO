from ginkgo.data.models.base_model import BaseModel
from ginkgo.enums import OrderType, OrderStatus, Direction
from sqlalchemy import Column, String, Boolean, func, Integer, DECIMAL, Enum
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from clickhouse_sqlalchemy import engines


class Order(BaseModel):
    __abstract__ = False
    __tablename__ = "Orders"

    if GINKGOCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.Memory(),)

    code = Column(String(12), default="default")
    # direction = Column(Enum(Direction))
    # TYPE = Column(Enum("MARKET", "LIMITORDER"))
    # QUANTITY = Column(Integer)
    # PRICE = Column(DECIMAL(10, 2))
    # STATUS = Column(Enum("NEW", "SUBMITTED", "FILLED", "CANCELED"))

    # @property
    # def dire(self):
    #     return Direction(self.direction)

    # @dire.setter
    # def dire(self, value):
    #     if isinstance(value, Direction):
    #         self.direction = value.value()
    #     elif isinstance(value, int):
    #         try:
    #             Direction(value)
    #             self.direction = value
    #         except Exception as e:
    #             print(e)
