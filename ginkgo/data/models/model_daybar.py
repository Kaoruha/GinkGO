from ginkgo.data.models.base_model import BaseModel
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from sqlalchemy import Column, String, Integer, DECIMAL
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from clickhouse_sqlalchemy import engines
from sqlalchemy_utils import ChoiceType


class Daybar(BaseModel):
    __abstract__ = False
    __tablename__ = "daybar"

    if GINKGOCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.Memory(),)

    code = Column(String(25), default="ginkgo_test_code")
    source = Column(ChoiceType(SOURCE_TYPES, impl=Integer()), default=1)
    p_open = Column(DECIMAL(9, 2), default=0)
    p_high = Column(DECIMAL(9, 2), default=0)
    p_low = Column(DECIMAL(9, 2), default=0)
    p_close = Column(DECIMAL(9, 2), default=0)
    volume = Column(Integer, default=0)
