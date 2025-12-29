# Upstream: PositionCRUD (持仓数据持久化)、Portfolio Manager (持仓记录查询)
# Downstream: MMysqlBase (继承提供MySQL ORM能力)、MBacktestRecordBase (继承提供回测记录基础字段)
# Role: MPosition持仓MySQL模型继承MMysqlBase定义持仓数据结构和字段支持回测支持交易系统功能和组件集成提供完整业务支持






import datetime
import pandas as pd
from typing import Union, Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal
from ginkgo.enums import SOURCE_TYPES


class MPosition(MMysqlBase, MBacktestRecordBase):
    __abstract__ = False
    __tablename__ = "position"

    portfolio_id: Mapped[str] = mapped_column(String(32), default="")
    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    cost: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    frozen_volume: Mapped[int] = mapped_column(Integer, default=0)
    settlement_frozen_volume: Mapped[int] = mapped_column(Integer, default=0, comment="T+N结算冻结持仓")
    settlement_days: Mapped[int] = mapped_column(Integer, default=0, comment="结算天数配置")
    settlement_queue_json: Mapped[str] = mapped_column(Text, default="[]", comment="结算队列JSON数据")
    frozen_money: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    price: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    fee: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    business_timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, comment="业务时间戳")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        run_id: str = "",  # 新增run_id参数
        code: Optional[str] = None,
        cost: Optional[Number] = None,
        volume: Optional[int] = None,
        frozen_volume: Optional[int] = None,
        settlement_frozen_volume: Optional[int] = None,
        settlement_days: Optional[int] = None,
        settlement_queue_json: Optional[str] = None,
        frozen_money: Optional[Number] = None,
        price: Optional[Number] = None,
        fee: Optional[Number] = None,
        source: Optional[SOURCE_TYPES] = None,
        business_timestamp: Optional[any] = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        self.engine_id = engine_id
        self.run_id = run_id  # 新增run_id字段赋值
        if code is not None:
            self.code = str(code)
        if cost is not None:
            self.cost = to_decimal(cost)
        if volume is not None:
            self.volume = int(volume)
        if frozen_volume is not None:
            self.frozen_volume = int(frozen_volume)
        if settlement_frozen_volume is not None:
            self.settlement_frozen_volume = int(settlement_frozen_volume)
        if settlement_days is not None:
            self.settlement_days = int(settlement_days)
        if settlement_queue_json is not None:
            self.settlement_queue_json = str(settlement_queue_json)
        if frozen_money is not None:
            self.frozen_money = to_decimal(frozen_money)
        if price is not None:
            self.price = to_decimal(price)
        if fee is not None:
            self.fee = to_decimal(fee)
        if source is not None:
            self.set_source(source)
        if business_timestamp is not None:
            self.business_timestamp = datetime_normalize(business_timestamp)
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.engine_id = df["engine_id"]
        self.code = df["code"]
        self.cost = to_decimal(df["cost"])
        self.volume = df["volume"]
        self.frozen_volume = df["frozen_volume"]
        self.settlement_frozen_volume = df["settlement_frozen_volume"]
        self.settlement_days = df["settlement_days"]
        self.frozen_money = df["frozen_money"]
        self.price = df["price"]
        self.fee = df["fee"]

        if "business_timestamp" in df.keys() and pd.notna(df["business_timestamp"]):
            self.business_timestamp = datetime_normalize(df["business_timestamp"])
        if "source" in df.keys():
            self.set_source(df["source"])
        self.update_at = datetime.datetime.now()

    def __init__(self, **kwargs):
        """初始化MPosition实例，自动处理枚举字段转换"""
        super().__init__()
        # 处理source字段的枚举转换
        if 'source' in kwargs:
            self.set_source(kwargs['source'])
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
