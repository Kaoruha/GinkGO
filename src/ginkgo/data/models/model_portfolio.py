import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, DECIMAL, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.trading.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize


class MPortfolio(MMysqlBase):
    """
    Similar to backtest.
    """

    __abstract__ = False
    __tablename__ = "portfolio"

    name: Mapped[str] = mapped_column(String(64), default="default_live")
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    backtest_start_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    backtest_end_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)

    # 投资组合核心业务字段
    initial_capital: Mapped[DECIMAL] = mapped_column(DECIMAL(20, 8), default=100000.00)
    current_capital: Mapped[DECIMAL] = mapped_column(DECIMAL(20, 8), default=100000.00)
    cash: Mapped[DECIMAL] = mapped_column(DECIMAL(20, 8), default=100000.00)
    frozen: Mapped[DECIMAL] = mapped_column(DECIMAL(20, 8), default=0.00)
    total_fee: Mapped[DECIMAL] = mapped_column(DECIMAL(20, 8), default=0.00)
    total_profit: Mapped[DECIMAL] = mapped_column(DECIMAL(20, 8), default=0.00)
    risk_level: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 4), default=0.10)

    # 性能指标字段
    max_drawdown: Mapped[DECIMAL] = mapped_column(DECIMAL(20, 8), default=0.00)
    sharpe_ratio: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 4), default=0.00)
    win_rate: Mapped[DECIMAL] = mapped_column(DECIMAL(5, 4), default=0.00)
    total_trades: Mapped[int] = mapped_column(default=0)
    winning_trades: Mapped[int] = mapped_column(default=0)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        name: str,
        description: Optional[str] = None,
        backtest_start_date: Optional[any] = None,
        backtest_end_date: Optional[any] = None,
        is_live: Optional[bool] = None,
        source: Optional[SOURCE_TYPES] = None,
        initial_capital: Optional[float] = None,
        current_capital: Optional[float] = None,
        cash: Optional[float] = None,
        frozen: Optional[float] = None,
        total_fee: Optional[float] = None,
        total_profit: Optional[float] = None,
        risk_level: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        sharpe_ratio: Optional[float] = None,
        win_rate: Optional[float] = None,
        total_trades: Optional[int] = None,
        winning_trades: Optional[int] = None,
        *args,
        **kwargs
    ) -> None:
        self.name = name
        if description is not None:
            self.description = description
        if backtest_start_date is not None:
            self.backtest_start_date = datetime_normalize(backtest_start_date)
        if backtest_end_date is not None:
            self.backtest_end_date = datetime_normalize(backtest_end_date)
        if is_live is not None:
            self.is_live = is_live
        if source is not None:
            self.source = source

        # 更新业务字段
        if initial_capital is not None:
            self.initial_capital = initial_capital
        if current_capital is not None:
            self.current_capital = current_capital
        if cash is not None:
            self.cash = cash
        if frozen is not None:
            self.frozen = frozen
        if total_fee is not None:
            self.total_fee = total_fee
        if total_profit is not None:
            self.total_profit = total_profit
        if risk_level is not None:
            self.risk_level = risk_level

        # 更新性能指标
        if max_drawdown is not None:
            self.max_drawdown = max_drawdown
        if sharpe_ratio is not None:
            self.sharpe_ratio = sharpe_ratio
        if win_rate is not None:
            self.win_rate = win_rate
        if total_trades is not None:
            self.total_trades = total_trades
        if winning_trades is not None:
            self.winning_trades = winning_trades

        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        # TODO
        self.name = df["name"]
        self.backtest_start_date = datetime_normalize(df["backtest_start_date"])
        self.backtest_end_date = datetime_normalize(df["backtest_end_date"])
        self.is_live = df["is_live"]
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
