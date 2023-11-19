import datetime
import pandas as pd
from sqlalchemy import Column, String, Integer, DECIMAL
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs import base_repr, datetime_normalize


class MAnalyzer(MClickBase):
    __abstract__ = False
    __tablename__ = "analyzer"

    name = Column(String(), default="Default Profit")
    value = Column(DECIMAL(20, 10), default=0)
    backtest_id = Column(String(), default="Default Profit")
    analyzer_id = Column(String(), default="Default Analyzer")

    def __init__(self, *args, **kwargs) -> None:
        super(MAnalyzer, self).__init__(*args, **kwargs)

    def set(
        self,
        analyzer_name: str,
        timestamp: any,
        value: str,
        backtest_id: str,
        analyzer_id: id,
    ) -> None:
        self.name = analyzer_name
        self.backtest_id = backtest_id
        self.analyzer_id = analyzer_id
        self.timestamp = datetime_normalize(datetime)
        self.value = value

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
