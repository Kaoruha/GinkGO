# Upstream: Backtest Engines (调用cal方法)
# Downstream: BaseStrategy, IDataFeeder, DIRECTION_TYPES
# Role: Dual Thrust策略 — 通过 data_feeder 获取历史K线计算突破区间






import datetime
from decimal import Decimal
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.entities import Signal
from ginkgo.libs import GLOG
import pandas as pd


class StrategyDualThrust(BaseStrategy):
    __abstract__ = False

    def __init__(
        self,
        name: str = "DualThrust",
        spans: int = 7,
        k_buy: float = 0.5,
        k_sell: float = 0.5,
        *args,
        **kwargs,
    ):
        super().__init__(name, *args, **kwargs)
        self._spans = spans
        self._k_buy = Decimal(str(k_buy))
        self._k_sell = Decimal(str(k_sell))

    def _calculate_range(self, df: pd.DataFrame) -> Decimal:
        """
        Calculates the range for the Dual Thrust strategy.
        """
        hh = df["high"].rolling(window=self._spans).max().iloc[-1]
        lc = df["close"].rolling(window=self._spans).min().iloc[-1]
        hc = df["close"].rolling(window=self._spans).max().iloc[-1]
        ll = df["low"].rolling(window=self._spans).min().iloc[-1]
        return max(hh - lc, hc - ll)

    def _generate_signal(
        self, portfolio_info, code: str, direction: DIRECTION_TYPES
    ) -> Signal:
        """
        Generates a signal for the given code and direction.
        """
        GLOG.INFO(f"Gen {direction.value} Signal about {code} from {self.name}")
        return self.create_signal(
            code=code,
            direction=direction,
            reason="Dual Thrust",
            business_timestamp=portfolio_info.get("now"),
        )

    def cal(self, portfolio_info, event, *args, **kwargs):
        super().cal(portfolio_info, event)
        date_start = self.business_timestamp - datetime.timedelta(days=(self._spans + 1))
        df = self.data_feeder.get_historical_data(
            symbols=[event.code], start_time=date_start,
            end_time=self.business_timestamp, data_type="bar"
        )

        if df is None or df.empty or df.shape[0] < self._spans + 1:
            return []

        today_r = self._calculate_range(df)
        today_buy_line = df.iloc[-1]["open"] + self._k_buy * today_r
        today_sell_line = df.iloc[-1]["open"] - self._k_sell * today_r

        last_r = self._calculate_range(df.iloc[:-1])
        last_buy_line = df.iloc[-2]["open"] + self._k_buy * last_r
        last_sell_line = df.iloc[-2]["open"] - self._k_sell * last_r

        has_position = event.code in portfolio_info["positions"]

        if (
            df.iloc[-2]["close"] < last_buy_line
            and df.iloc[-1]["close"] > today_buy_line
            and not has_position
        ):
            return [self._generate_signal(portfolio_info, event.code, DIRECTION_TYPES.LONG)]

        if (
            df.iloc[-2]["close"] > last_sell_line
            and df.iloc[-1]["close"] < today_sell_line
            and has_position
        ):
            return [self._generate_signal(portfolio_info, event.code, DIRECTION_TYPES.SHORT)]

        return []