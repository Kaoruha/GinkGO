# Upstream: PortfolioService (投资组合管理)、Backtest Engines (创建和查询portfolio)
# Downstream: MMysqlBase (继承提供MySQL ORM能力)
# Role: MPortfolio投资组合MySQL模型继承MMysqlBase定义核心字段提供投资组合配置管理支持交易系统功能和组件集成提供完整业务支持






import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, DECIMAL, DateTime, Boolean, Integer
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.trading.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, PORTFOLIO_MODE_TYPES, PORTFOLIO_RUNSTATE_TYPES
from ginkgo.libs import base_repr, datetime_normalize


class MPortfolio(MMysqlBase):
    """
    Portfolio model with mode and state support.
    """

    __abstract__ = False
    __tablename__ = "portfolio"

    name: Mapped[str] = mapped_column(String(64), default="default_portfolio")
    desc: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Portfolio mode: BACKTEST(0), PAPER(1), LIVE(2)
    mode: Mapped[int] = mapped_column(TINYINT, default=0, comment="运行模式: 0=回测, 1=模拟盘, 2=实盘")

    # Portfolio state: INITIALIZED(0), RUNNING(1), PAUSED(2), STOPPING(3), STOPPED(4), RELOADING(5), MIGRATING(6)
    state: Mapped[int] = mapped_column(TINYINT, default=0, comment="运行状态: 0=已初始化, 1=运行中, 2=已暂停, 3=停止中, 4=已停止, 5=重载中, 6=迁移中")

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
        mode: Optional[int] = None,
        state: Optional[int] = None,
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
            self.desc = description
        if mode is not None:
            self.mode = PORTFOLIO_MODE_TYPES.validate_input(mode) or PORTFOLIO_MODE_TYPES.BACKTEST.value
        if state is not None:
            self.state = PORTFOLIO_RUNSTATE_TYPES.validate_input(state) or PORTFOLIO_RUNSTATE_TYPES.INITIALIZED.value
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

        self.updated_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        # TODO
        self.name = df["name"]
        if "mode" in df.keys():
            self.mode = PORTFOLIO_MODE_TYPES.validate_input(df["mode"]) or PORTFOLIO_MODE_TYPES.BACKTEST.value
        if "state" in df.keys():
            self.state = PORTFOLIO_RUNSTATE_TYPES.validate_input(df["state"]) or PORTFOLIO_RUNSTATE_TYPES.INITIALIZED.value
        if "source" in df.keys():
            self.source = df["source"]
        self.updated_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
