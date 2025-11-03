import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, Enum
from clickhouse_sqlalchemy import types
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
from ginkgo.trading.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize


class MSignal(MClickBase, MBacktestRecordBase):
    __abstract__ = False
    __tablename__ = "signal"

    portfolio_id: Mapped[str] = mapped_column(String(), default="")
    code: Mapped[str] = mapped_column(String(), default="ginkgo_test_code")
    direction: Mapped[int] = mapped_column(types.Int8, default=-1)
    reason: Mapped[str] = mapped_column(String(), default="")
    volume: Mapped[int] = mapped_column(types.Int64, default=0)  # 建议交易量
    weight: Mapped[float] = mapped_column(types.Float32, default=0.0)  # 信号权重或资金分配比例
    strength: Mapped[float] = mapped_column(types.Float32, default=0.5)
    confidence: Mapped[float] = mapped_column(types.Float32, default=0.5)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        run_id: str = "",  # 新增run_id参数
        timestamp: Optional[any] = None,
        code: Optional[str] = None,
        direction: Optional[DIRECTION_TYPES] = None,
        reason: Optional[str] = None,
        source: Optional[SOURCE_TYPES] = None,
        volume: Optional[int] = None,
        weight: Optional[float] = None,
        strength: Optional[float] = None,
        confidence: Optional[float] = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        self.engine_id = engine_id
        self.run_id = run_id  # 新增run_id字段赋值
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if code is not None:
            self.code = code
        if direction is not None:
            self.direction = DIRECTION_TYPES.validate_input(direction) or -1
        if reason is not None:
            self.reason = reason
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or -1
        if volume is not None:
            self.volume = int(volume)
        if weight is not None:
            self.weight = float(weight)
        if strength is not None:
            self.strength = float(strength)
        if confidence is not None:
            self.confidence = float(confidence)

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.engine_id = df["engine_id"]
        self.timestamp = datetime_normalize(df["timestamp"])
        self.code = df["code"]
        self.direction = DIRECTION_TYPES.validate_input(df["direction"]) or -1
        self.reason = df["reason"]

        if "source" in df.keys():
            self.source = SOURCE_TYPES.validate_input(df["source"]) or -1
        self.update_at = datetime.datetime.now()

    def __init__(self, **kwargs):
        """初始化MSignal实例，自动处理枚举字段转换"""
        super().__init__()
        # 处理direction和source字段的枚举转换
        if 'direction' in kwargs:
            from ginkgo.enums import DIRECTION_TYPES
            result = DIRECTION_TYPES.validate_input(kwargs['direction'])
            self.direction = result if result is not None else -1
            del kwargs['direction']
        if 'source' in kwargs:
            self.set_source(kwargs['source'])
            # 从kwargs中移除source，避免重复赋值
            del kwargs['source']
        # 设置其他字段
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
