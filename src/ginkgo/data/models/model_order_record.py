# Upstream: AnalyzerService, order_record_crud, 分析器(回测指标统计)
# Downstream: MClickBase, MBacktestRecordBase, 订单相关枚举
# Role: 订单记录ClickHouse模型，存储回测/模拟盘产生的订单快照(价格/数量/状态/费用)






import datetime
import pandas as pd
from typing import Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import String, Integer, DECIMAL, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from clickhouse_sqlalchemy import types

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal


class MOrderRecord(MClickBase, MBacktestRecordBase):
    __abstract__ = False
    __tablename__ = "order_record"

    order_id: Mapped[str] = mapped_column(String(), default="")
    portfolio_id: Mapped[str] = mapped_column(String(), default="")
    code: Mapped[str] = mapped_column(String(), default="ginkgo_test_code")
    direction: Mapped[int] = mapped_column(types.Int8, default=-1, info={"enum": DIRECTION_TYPES})
    # 血缘(2026-08-17 追溯链 Signal→Order→PositionRecord):触发本订单的信号 uuid。
    # 由 on_signal 挂载、_save_order_record 统一写入,三态行(NEW/SUBMITTED/FILLED)全覆盖
    signal_id: Mapped[str] = mapped_column(String(), default="", comment="触发订单的信号uuid")
    order_type: Mapped[int] = mapped_column(types.Int8, default=-1)
    status: Mapped[int] = mapped_column(types.Int8, default=-1)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    limit_price: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    frozen_money: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    frozen_volume: Mapped[int] = mapped_column(Integer, default=0)
    transaction_price: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    transaction_volume: Mapped[int] = mapped_column(Integer, default=0)
    remain: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    fee: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    business_timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, comment="业务时间戳")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        order_id: str,
        portfolio_id: str,
        engine_id: str,
        code: Optional[str] = None,
        direction: Optional[DIRECTION_TYPES] = None,
        order_type: Optional[ORDER_TYPES] = None,
        status: Optional[ORDERSTATUS_TYPES] = None,
        volume: Optional[int] = None,
        limit_price: Optional[Number] = None,
        frozen_money: Optional[Number] = None,
        frozen_volume: Optional[int] = None,
        transaction_price: Optional[Number] = None,
        transaction_volume: Optional[int] = None,
        remain: Optional[Number] = None,
        fee: Optional[Number] = None,
        timestamp: Optional[any] = None,
        business_timestamp: Optional[any] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.order_id = order_id
        self.portfolio_id = portfolio_id
        self.engine_id = engine_id
        if code is not None:
            self.code = code
        if direction is not None:
            # validate_input 对 OTHER(0) 返 0(合法值);`or -1` 会误吞为 -1 → 仅 None 兜底
            validated = DIRECTION_TYPES.validate_input(direction)
            self.direction = validated if validated is not None else -1
        if order_type is not None:
            validated = ORDER_TYPES.validate_input(order_type)
            self.order_type = validated if validated is not None else -1
        if status is not None:
            validated = ORDERSTATUS_TYPES.validate_input(status)
            self.status = validated if validated is not None else -1
        if volume is not None:
            self.volume = volume
        if limit_price is not None:
            self.limit_price = to_decimal(limit_price)
        if frozen_money is not None:
            self.frozen_money = to_decimal(frozen_money)
        if frozen_volume is not None:
            self.frozen_volume = int(frozen_volume)  # #6087: 强制 int，防 float 写 Integer 列
        if transaction_price is not None:
            self.transaction_price = to_decimal(transaction_price)
        if transaction_volume is not None:
            self.transaction_volume = transaction_volume
        if remain is not None:
            self.remain = to_decimal(remain)
        if fee is not None:
            self.fee = to_decimal(fee)
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if business_timestamp is not None:
            self.business_timestamp = datetime_normalize(business_timestamp)
        if source is not None:
            self.set_source(source)

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.order_id = df["order_id"]
        self.portfolio_id = df["portfolio_id"]
        self.engine_id = df["engine_id"]
        self.code = df["code"]
        validated = DIRECTION_TYPES.validate_input(df["direction"])
        self.direction = validated if validated is not None else -1
        validated = ORDER_TYPES.validate_input(df["order_type"])
        self.order_type = validated if validated is not None else -1
        validated = ORDERSTATUS_TYPES.validate_input(df["status"])
        self.status = validated if validated is not None else -1
        self.volume = df["volume"]
        self.limit_price = to_decimal(df["limit_price"])
        self.frozen_money = to_decimal(df["frozen_money"] if "frozen_money" in df else df.get("frozen", 0))
        self.frozen_volume = int(df["frozen_volume"] if "frozen_volume" in df else 0)
        self.transaction_price = to_decimal(df["transaction_price"])
        self.transaction_volume = df["transaction_volume"]
        self.remain = to_decimal(df["remain"])
        self.fee = to_decimal(df["fee"])
        self.timestamp = datetime_normalize(df["timestamp"])
        if "business_timestamp" in df.keys() and pd.notna(df["business_timestamp"]):
            self.business_timestamp = datetime_normalize(df["business_timestamp"])
        self.portfolio_id = df["portfolio_id"]
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __init__(self, **kwargs):
        """初始化MOrderRecord实例，自动处理枚举字段转换"""
        super().__init__()
        # 处理枚举字段转换
        if 'direction' in kwargs:
            validated = DIRECTION_TYPES.validate_input(kwargs['direction'])
            self.direction = validated if validated is not None else -1
            del kwargs['direction']
        if 'order_type' in kwargs:
            validated = ORDER_TYPES.validate_input(kwargs['order_type'])
            self.order_type = validated if validated is not None else -1
            del kwargs['order_type']
        if 'status' in kwargs:
            validated = ORDERSTATUS_TYPES.validate_input(kwargs['status'])
            self.status = validated if validated is not None else -1
            del kwargs['status']
        if 'source' in kwargs:
            self.set_source(kwargs['source'])
            del kwargs['source']
        # 处理business_timestamp字段
        if 'business_timestamp' in kwargs:
            self.business_timestamp = datetime_normalize(kwargs['business_timestamp'])
            del kwargs['business_timestamp']
        # 设置其他字段
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key == 'frozen_volume' and value is not None:
                    value = int(value)  # #6087: 强制 int，防 float 写 Integer 列
                setattr(self, key, value)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)

