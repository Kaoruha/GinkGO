import pandas as pd
import datetime
from typing import Optional
from functools import singledispatchmethod
from decimal import Decimal

from sqlalchemy import String, Integer, DECIMAL, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EXECUTION_MODE, TRACKING_STATUS, ACCOUNT_TYPE
from ginkgo.libs import base_repr, datetime_normalize, to_decimal


class MSignalTracker(MMysqlBase, MBacktestRecordBase):
    """
    信号追踪模型

    用于追踪模拟盘和实盘的信号执行情况，支持人工确认流程
    """
    __abstract__ = False
    __tablename__ = "signal_tracker"

    # 关联信息
    signal_id: Mapped[str] = mapped_column(String(32), index=True, comment="关联的信号ID")
    strategy_id: Mapped[str] = mapped_column(String(32), index=True, comment="策略ID")
    portfolio_id: Mapped[str] = mapped_column(String(32), index=True, comment="投资组合ID")

    # 执行模式
    execution_mode: Mapped[int] = mapped_column(Integer, default=0, comment="执行模式")
    account_type: Mapped[int] = mapped_column(Integer, default=1, comment="账户类型: 0=回测,1=模拟盘,2=实盘")
    
    # 预期执行参数
    expected_code: Mapped[str] = mapped_column(String(20), comment="股票代码")
    expected_direction: Mapped[int] = mapped_column(Integer, comment="交易方向")
    expected_price: Mapped[Decimal] = mapped_column(DECIMAL(16, 4), comment="预期价格")
    expected_volume: Mapped[int] = mapped_column(Integer, comment="预期数量")
    expected_timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), comment="预期执行时间")
    
    # 实际执行参数
    actual_price: Mapped[Decimal] = mapped_column(DECIMAL(16, 4), nullable=True, comment="实际价格")
    actual_volume: Mapped[int] = mapped_column(Integer, nullable=True, comment="实际数量")
    actual_timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True, comment="实际执行时间")
    
    # 状态追踪
    tracking_status: Mapped[int] = mapped_column(Integer, default=0, comment="追踪状态")
    notification_sent_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now, comment="通知发送时间")
    execution_confirmed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True, comment="执行确认时间")
    
    # 偏差指标
    price_deviation: Mapped[Decimal] = mapped_column(DECIMAL(8, 4), nullable=True, comment="价格偏差")
    volume_deviation: Mapped[Decimal] = mapped_column(DECIMAL(8, 4), nullable=True, comment="数量偏差")
    time_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=True, comment="时间延迟(秒)")
    
    # 其他信息
    reject_reason: Mapped[str] = mapped_column(String(200), nullable=True, comment="拒绝原因")
    notes: Mapped[str] = mapped_column(String(500), nullable=True, comment="备注")

    def __init__(self,
                 signal_id=None, strategy_id=None, portfolio_id=None,
                 execution_mode=None, account_type=None,
                 expected_code=None, expected_direction=None, expected_price=None,
                 expected_volume=None, expected_timestamp=None,
                 actual_price=None, actual_volume=None, actual_timestamp=None,
                 tracking_status=None, notification_sent_at=None, execution_confirmed_at=None,
                 price_deviation=None, volume_deviation=None, time_delay_seconds=None,
                 reject_reason=None, notes=None, source=None, **kwargs):
        """Initialize MSignalTracker with automatic enum/int handling"""
        super().__init__(**kwargs)

        # 关联信息
        if signal_id is not None:
            self.signal_id = signal_id
        if strategy_id is not None:
            self.strategy_id = strategy_id
        if portfolio_id is not None:
            self.portfolio_id = portfolio_id

        # 执行模式 - 自动转换枚举
        if execution_mode is not None:
            self.execution_mode = EXECUTION_MODE.validate_input(execution_mode) or EXECUTION_MODE.SIMULATION.value
        if account_type is not None:
            self.account_type = ACCOUNT_TYPE.validate_input(account_type) or ACCOUNT_TYPE.PAPER.value

        # 预期执行参数
        if expected_code is not None:
            self.expected_code = expected_code
        if expected_direction is not None:
            self.expected_direction = DIRECTION_TYPES.validate_input(expected_direction) or DIRECTION_TYPES.LONG.value
        if expected_price is not None:
            self.expected_price = to_decimal(expected_price)
        if expected_volume is not None:
            self.expected_volume = expected_volume
        if expected_timestamp is not None:
            self.expected_timestamp = datetime_normalize(expected_timestamp)

        # 实际执行参数
        if actual_price is not None:
            self.actual_price = to_decimal(actual_price)
        if actual_volume is not None:
            self.actual_volume = actual_volume
        if actual_timestamp is not None:
            self.actual_timestamp = datetime_normalize(actual_timestamp)

        # 状态追踪 - 自动转换枚举
        if tracking_status is not None:
            self.tracking_status = TRACKING_STATUS.validate_input(tracking_status) or TRACKING_STATUS.NOTIFIED.value
        if notification_sent_at is not None:
            self.notification_sent_at = datetime_normalize(notification_sent_at)
        if execution_confirmed_at is not None:
            self.execution_confirmed_at = datetime_normalize(execution_confirmed_at)

        # 偏差指标
        if price_deviation is not None:
            self.price_deviation = to_decimal(price_deviation)
        if volume_deviation is not None:
            self.volume_deviation = to_decimal(volume_deviation)
        if time_delay_seconds is not None:
            self.time_delay_seconds = time_delay_seconds

        # 其他信息
        if reject_reason is not None:
            self.reject_reason = reject_reason
        if notes is not None:
            self.notes = notes
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or SOURCE_TYPES.TUSHARE.value

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        signal_id: str,
        strategy_id: str,
        portfolio_id: str,
        execution_mode: EXECUTION_MODE,
        account_type: ACCOUNT_TYPE,
        expected_code: str,
        expected_direction: DIRECTION_TYPES,
        expected_price: float,
        expected_volume: int,
        expected_timestamp: datetime.datetime,
        engine_id: Optional[str] = None,
        run_id: Optional[str] = None,
        actual_price: Optional[float] = None,
        actual_volume: Optional[int] = None,
        actual_timestamp: Optional[datetime.datetime] = None,
        tracking_status: Optional[TRACKING_STATUS] = None,
        notification_sent_at: Optional[datetime.datetime] = None,
        execution_confirmed_at: Optional[datetime.datetime] = None,
        price_deviation: Optional[float] = None,
        volume_deviation: Optional[float] = None,
        time_delay_seconds: Optional[int] = None,
        reject_reason: Optional[str] = None,
        notes: Optional[str] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.signal_id = signal_id
        self.strategy_id = strategy_id
        self.portfolio_id = portfolio_id
        self.execution_mode = EXECUTION_MODE.validate_input(execution_mode) or 0
        self.account_type = ACCOUNT_TYPE.validate_input(account_type) or 1
        
        # 预期参数
        self.expected_code = expected_code
        self.expected_direction = DIRECTION_TYPES.validate_input(expected_direction) or -1
        self.expected_price = to_decimal(expected_price)
        self.expected_volume = expected_volume
        self.expected_timestamp = datetime_normalize(expected_timestamp)
        
        if engine_id is not None:
            self.engine_id = engine_id
        if run_id is not None:
            self.run_id = run_id

        # 实际执行参数
        if actual_price is not None:
            self.actual_price = to_decimal(actual_price)
        if actual_volume is not None:
            self.actual_volume = actual_volume
        if actual_timestamp is not None:
            self.actual_timestamp = datetime_normalize(actual_timestamp)
        
        # 状态信息
        if tracking_status is not None:
            self.tracking_status = TRACKING_STATUS.validate_input(tracking_status) or 0
        if notification_sent_at is not None:
            self.notification_sent_at = datetime_normalize(notification_sent_at)
        if execution_confirmed_at is not None:
            self.execution_confirmed_at = datetime_normalize(execution_confirmed_at)
        
        # 偏差指标
        if price_deviation is not None:
            self.price_deviation = to_decimal(price_deviation)
        if volume_deviation is not None:
            self.volume_deviation = to_decimal(volume_deviation)
        if time_delay_seconds is not None:
            self.time_delay_seconds = time_delay_seconds
        
        # 其他信息
        if reject_reason is not None:
            self.reject_reason = reject_reason
        if notes is not None:
            self.notes = notes
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or -1
        
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.signal_id = df["signal_id"]
        self.strategy_id = df["strategy_id"]
        self.portfolio_id = df["portfolio_id"]
        self.execution_mode = EXECUTION_MODE.validate_input(df["execution_mode"]) or 0
        self.account_type = ACCOUNT_TYPE.validate_input(df["account_type"]) or 1
        
        # 预期参数
        self.expected_code = df["expected_code"]
        self.expected_direction = DIRECTION_TYPES.validate_input(df["expected_direction"]) or -1
        self.expected_price = to_decimal(df["expected_price"])
        self.expected_volume = df["expected_volume"]
        self.expected_timestamp = datetime_normalize(df["expected_timestamp"])
        
        if "engine_id" in df.keys():
            self.engine_id = df["engine_id"]
        
        # 实际执行参数
        if "actual_price" in df.keys() and pd.notna(df["actual_price"]):
            self.actual_price = to_decimal(df["actual_price"])
        if "actual_volume" in df.keys() and pd.notna(df["actual_volume"]):
            self.actual_volume = df["actual_volume"]
        if "actual_timestamp" in df.keys() and pd.notna(df["actual_timestamp"]):
            self.actual_timestamp = datetime_normalize(df["actual_timestamp"])
        
        # 状态信息
        if "tracking_status" in df.keys():
            self.tracking_status = TRACKING_STATUS.validate_input(df["tracking_status"]) or 0
        if "notification_sent_at" in df.keys():
            self.notification_sent_at = datetime_normalize(df["notification_sent_at"])
        if "execution_confirmed_at" in df.keys() and pd.notna(df["execution_confirmed_at"]):
            self.execution_confirmed_at = datetime_normalize(df["execution_confirmed_at"])
        
        # 偏差指标
        if "price_deviation" in df.keys() and pd.notna(df["price_deviation"]):
            self.price_deviation = to_decimal(df["price_deviation"])
        if "volume_deviation" in df.keys() and pd.notna(df["volume_deviation"]):
            self.volume_deviation = to_decimal(df["volume_deviation"])
        if "time_delay_seconds" in df.keys() and pd.notna(df["time_delay_seconds"]):
            self.time_delay_seconds = df["time_delay_seconds"]
        
        # 其他信息
        if "reject_reason" in df.keys() and pd.notna(df["reject_reason"]):
            self.reject_reason = df["reject_reason"]
        if "notes" in df.keys() and pd.notna(df["notes"]):
            self.notes = df["notes"]
        if "source" in df.keys():
            self.source = SOURCE_TYPES.validate_input(df["source"]) or -1
        
        self.update_at = datetime.datetime.now()

    def calculate_deviations(self):
        """计算执行偏差"""
        if self.actual_price and self.actual_volume:
            # 价格偏差 = (实际价格 - 预期价格) / 预期价格
            self.price_deviation = (self.actual_price - self.expected_price) / self.expected_price
            
            # 数量偏差 = (实际数量 - 预期数量) / 预期数量
            self.volume_deviation = (self.actual_volume - self.expected_volume) / self.expected_volume
            
            # 时间延迟
            if self.actual_timestamp:
                self.time_delay_seconds = (self.actual_timestamp - self.expected_timestamp).total_seconds()

    def is_executed(self) -> bool:
        """判断是否已执行"""
        return self.tracking_status == TRACKING_STATUS.EXECUTED.value

    def is_pending(self) -> bool:
        """判断是否等待确认"""
        return self.tracking_status == TRACKING_STATUS.NOTIFIED.value

    def is_timeout(self) -> bool:
        """判断是否超时"""
        return self.tracking_status == TRACKING_STATUS.TIMEOUT.value

    def get_account_type_name(self) -> str:
        """获取账户类型名称"""
        account_type_enum = ACCOUNT_TYPE.from_int(self.account_type)
        if account_type_enum == ACCOUNT_TYPE.PAPER:
            return "模拟盘"
        elif account_type_enum == ACCOUNT_TYPE.LIVE:
            return "实盘"
        elif account_type_enum == ACCOUNT_TYPE.BACKTEST:
            return "回测"
        else:
            return "未知"

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)