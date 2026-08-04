# Upstream: TickService (同步逐笔成交数据)、TickCRUD (CRUD操作)
# Downstream: MClickBase (继承提供ClickHouse ORM能力)、TICKDIRECTION_TYPES (枚举类型验证)
# Role: MTick逐笔成交ClickHouse模型继承MClickBase定义核心字段使用MergeTree






import pandas as pd
import datetime
from typing import Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, Enum
from sqlalchemy.orm import Mapped, mapped_column
from clickhouse_sqlalchemy import types

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs import datetime_normalize, base_repr, Number, to_decimal
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES


class MTick(MClickBase):
    __abstract__ = True
    __tablename__ = "tick"

    code: Mapped[str] = mapped_column(String(), default="ginkgo_test_code")
    price: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    direction: Mapped[int] = mapped_column(types.Int8, default=-1)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        code: str,
        price: Optional[Number] = None,
        volume: Optional[int] = None,
        direction: Optional[TICKDIRECTION_TYPES] = None,
        timestamp: Optional[any] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.code = code
        if price is not None:
            self.price = to_decimal(price)
        if volume is not None:
            self.volume = volume
        if direction is not None:
            # 或-1 仅在 validate_input 返 None 时兜底；0 是合法值（NEUTRAL），不可被 or 吞掉（ADR-029 Task 2 契约暴露）
            validated = TICKDIRECTION_TYPES.validate_input(direction)
            self.direction = validated if validated is not None else -1
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if source is not None:
            # 同上：0 是合法值（OTHER），or-1 会误判为缺失
            validated = SOURCE_TYPES.validate_input(source)
            self.source = validated if validated is not None else -1

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df["code"]
        self.price = to_decimal(df["price"])
        self.volume = df["volume"]
        validated = TICKDIRECTION_TYPES.validate_input(df["direction"])
        self.direction = validated if validated is not None else -1
        self.timestamp = datetime_normalize(df["timestamp"])
        if "source" in df.keys():
            validated = SOURCE_TYPES.validate_input(df["source"])
            self.source = validated if validated is not None else -1
        self.update_at = datetime.datetime.now()

    def __init__(self, **kwargs):
        """初始化MTick实例，自动处理枚举字段转换"""
        super().__init__()
        # 处理direction和source字段的枚举转换
        if 'direction' in kwargs:
            from ginkgo.enums import TICKDIRECTION_TYPES
            result = TICKDIRECTION_TYPES.validate_input(kwargs['direction'])
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

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
