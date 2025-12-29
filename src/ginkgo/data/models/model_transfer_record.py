# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: Model Transfer Record模型继承定义MTransferRecord划转记录相关数据结构






import pandas as pd
import datetime
from typing import Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import DateTime, String, DECIMAL, Enum
from clickhouse_sqlalchemy import types
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES, TRANSFERDIRECTION_TYPES


class MTransferRecord(MClickBase, MBacktestRecordBase, ModelConversion):
    __abstract__ = False
    __tablename__ = "transfer_record"

    portfolio_id: Mapped[str] = mapped_column(String(), default="")
    direction: Mapped[int] = mapped_column(types.Int8, default=-1)
    market: Mapped[int] = mapped_column(types.Int8, default=-1)
    money: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    status: Mapped[int] = mapped_column(types.Int8, default=-1)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        timestamp: Optional[any] = None,
        direction: Optional[TRANSFERDIRECTION_TYPES] = None,
        market: Optional[MARKET_TYPES] = None,
        money: Optional[Number] = None,
        status: Optional[TRANSFERSTATUS_TYPES] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        self.engine_id = engine_id
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if direction is not None:
            self.direction = TRANSFERDIRECTION_TYPES.validate_input(direction) or -1
        if market is not None:
            self.market = MARKET_TYPES.validate_input(market) or -1
        if money is not None:
            self.money = to_decimal(money)
        if status is not None:
            self.status = TRANSFERSTATUS_TYPES.validate_input(status) or -1
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or -1
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.engine_id = df["engine_id"]
        self.timestamp = datetime_normalize(df["timestamp"])
        self.direction = TRANSFERDIRECTION_TYPES.validate_input(df["direction"]) or -1
        self.market = MARKET_TYPES.validate_input(df["market"]) or -1
        self.money = to_decimal(df["money"])
        self.status = TRANSFERSTATUS_TYPES.validate_input(df["status"]) or -1
        if "source" in df.keys():
            self.source = SOURCE_TYPES.validate_input(df["source"]) or -1
        self.update_at = datetime.datetime.now()

    def __init__(self, **kwargs):
        """初始化MTransferRecord实例，自动处理枚举字段转换"""
        super().__init__()
        # 处理枚举字段转换
        if 'direction' in kwargs:
            self.direction = TRANSFERDIRECTION_TYPES.validate_input(kwargs['direction']) or -1
            del kwargs['direction']
        if 'market' in kwargs:
            self.market = MARKET_TYPES.validate_input(kwargs['market']) or -1
            del kwargs['market']
        if 'status' in kwargs:
            self.status = TRANSFERSTATUS_TYPES.validate_input(kwargs['status']) or -1
            del kwargs['status']
        if 'source' in kwargs:
            self.set_source(kwargs['source'])
            del kwargs['source']
        # 设置其他字段
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
