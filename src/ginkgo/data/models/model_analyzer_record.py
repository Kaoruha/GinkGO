import datetime
import pandas as pd

from functools import singledispatchmethod
from decimal import Decimal
from sqlalchemy import String, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.enums import SOURCE_TYPES
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs import base_repr, datetime_normalize


class MAnalyzerRecord(MClickBase):
    __abstract__ = False
    __tablename__ = "analyzer_record"

    portfolio_id: Mapped[str] = mapped_column(String(32), default="Default Profit")
    value: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    analyzer_id: Mapped[str] = mapped_column(String(32), default="Default Analyzer")
    name: Mapped[str] = mapped_column(String(32), default="Default Profit")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        timestamp: any = None,
        value: float = None,
        analyzer_id: id = None,
        name: str = None,
        source: SOURCE_TYPES = None,
        *args,
        **kwargs
    ) -> None:
        self.portfolio_id = portfolio_id
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if value is not None:
            self.value = round(value, 3)
        if name is not None:
            self.name = name
        if analyzer_id is not None:
            self.analyzer_id = analyzer_id
        if source is not None:
            self.source = source

    @update.register(pd.DataFrame)
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        # TODO
        if "source" in df.keys():
            self.source = df.source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
