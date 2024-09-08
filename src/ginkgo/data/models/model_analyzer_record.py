import datetime
import pandas as pd
from sqlalchemy import Column, String, Integer, DECIMAL
from decimal import Decimal
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs import base_repr, datetime_normalize


class MAnalyzerRecord(MClickBase):
    __abstract__ = False
    __tablename__ = "analyzer_record"

    name = Column(String(), default="Default Profit")
    value = Column(DECIMAL(20, 10), default=0)
    portfolio_id = Column(String(), default="Default Profit")
    analyzer_id = Column(String(), default="Default Analyzer")

    def __init__(self, *args, **kwargs) -> None:
        super(MAnalyzer, self).__init__(*args, **kwargs)

    def set(self, portfolio_id: str, timestamp: any, value: float, name: str, analyzer_id: id, *args, **kwargs) -> None:
        self.name = name
        self.portfolio_id = portfolio_id
        self.analyzer_id = analyzer_id
        self.timestamp = datetime_normalize(timestamp)
        self.value = round(value, 6)
        if self.value > 1000000000:
            self.value = Decimal(1000000000)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
