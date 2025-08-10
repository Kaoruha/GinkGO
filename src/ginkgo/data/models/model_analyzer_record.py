import datetime
import pandas as pd

from typing import Optional
from functools import singledispatchmethod
from decimal import Decimal
from sqlalchemy import String, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column

from ...enums import SOURCE_TYPES
from .model_clickbase import MClickBase
from ...libs import base_repr, datetime_normalize, Number, to_decimal


class MAnalyzerRecord(MClickBase):
    __abstract__ = False
    __tablename__ = "analyzer_record"

    portfolio_id: Mapped[str] = mapped_column(String(), default="Default Portfolio")
    engine_id: Mapped[str] = mapped_column(String(), default="Default Engine")
    value: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    analyzer_id: Mapped[str] = mapped_column(String(), default="Default Analyzer")
    name: Mapped[str] = mapped_column(String(), default="Default Analyter")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        timestamp: Optional[any] = None,
        value: Optional[Number] = None,
        analyzer_id: Optional[str] = None,
        name: Optional[str] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs
    ) -> None:
        self.portfolio_id = portfolio_id
        self.engine_id = engine_id
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if value is not None:
            self.value = to_decimal(value)
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
