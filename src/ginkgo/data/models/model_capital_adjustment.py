# Upstream: CapitalService (资金调整同步)、Portfolio Manager (资金变动记录)
# Downstream: MClickBase (继承提供ClickHouse ORM能力)、ModelConversion (提供实体转换能力)
# Role: MCapitalAdjustment资金调整模型继承MClickBase定义资金调整数据结构支持交易系统功能和组件集成提供完整业务支持






import pandas as pd
import datetime
from typing import Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import String, DECIMAL, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from clickhouse_sqlalchemy import engines, types

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.libs import datetime_normalize, base_repr, Number, to_decimal
from ginkgo.enums import SOURCE_TYPES


class MCapitalAdjustment(MClickBase, ModelConversion):
    __abstract__ = False
    __tablename__ = "capital_adjustment"

    # ClickHouse优化配置：按投资组合+时间排序
    __table_args__ = (
        engines.MergeTree(
            order_by=("portfolio_id", "timestamp")
        ),
        {"extend_existing": True},
    )

    """
    资金调整数据模型

    表示投资组合的资金调整操作，包括入金、出金、费用扣除等。
    与CapitalAdjustment业务对象完全对齐。
    """

    portfolio_id: Mapped[str] = mapped_column(types.String, default="", comment="投资组合ID")
    amount: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), default=0, comment="调整金额")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now, comment="调整时间")
    reason: Mapped[str] = mapped_column(types.String, default="", comment="调整原因")
    source: Mapped[int] = mapped_column(types.Int8, default=0, comment="数据源")
    business_timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, comment="业务时间戳")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        amount: Optional[Number] = None,
        timestamp: Optional[any] = None,
        reason: Optional[str] = None,
        source: Optional[SOURCE_TYPES] = None,
        business_timestamp: Optional[any] = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        if amount is not None:
            self.amount = to_decimal(amount)
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if reason is not None:
            self.reason = reason
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source)
        if business_timestamp is not None:
            self.business_timestamp = datetime_normalize(business_timestamp)

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.amount = to_decimal(df["amount"])
        self.timestamp = datetime_normalize(df["timestamp"])
        self.reason = df.get("reason", "")
        if "business_timestamp" in df.keys() and pd.notna(df["business_timestamp"]):
            self.business_timestamp = datetime_normalize(df["business_timestamp"])
        if "source" in df.keys():
            self.source = SOURCE_TYPES.validate_input(df["source"])

    def __init__(self, **kwargs):
        """初始化MCapitalAdjustment实例，自动处理枚举字段转换"""
        super().__init__()
        # 处理source字段的枚举转换
        if 'source' in kwargs:
            self.source = SOURCE_TYPES.validate_input(kwargs['source'])
            # 从kwargs中移除source，避免重复赋值
            del kwargs['source']
        # 处理business_timestamp字段
        if 'business_timestamp' in kwargs:
            self.business_timestamp = datetime_normalize(kwargs['business_timestamp'])
            del kwargs['business_timestamp']
        # 设置其他字段
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
