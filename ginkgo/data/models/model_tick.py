from ginkgo.data.models.model_base import MBase
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from sqlalchemy import Column, String, Integer, DECIMAL
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from clickhouse_sqlalchemy import engines
from sqlalchemy_utils import ChoiceType


class MTick(MBase):
    __abstract__ = False
    __tablename__ = "tick"

    if GINKGOCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.Memory(),)

    code = Column(String(25), default="ginkgo_test_code")
    direction = Column(ChoiceType(DIRECTION_TYPES, impl=Integer()), default=1)
    order_type = Column(ChoiceType(ORDER_TYPES, impl=Integer()), default=1)
    status = Column(ChoiceType(ORDERSTATUS_TYPES, impl=Integer()), default=1)
    source = Column(ChoiceType(SOURCE_TYPES, impl=Integer()), default=1)
    quantity = Column(Integer, default=0)
    price = Column(DECIMAL(9, 2), default=0)
