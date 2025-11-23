import datetime
from decimal import Decimal
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars
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
        super(StrategyDualThrust, self).__init__(name, *args, **kwargs)
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
        self.log("INFO", f"Gen {direction.value} Signal about {code} from {self.name}")
        return Signal(
            portfolio_id=portfolio_info["uuid"],
            engine_id=self.engine_id,
            timestamp=portfolio_info["now"],
            code=code,
            direction=direction,
            reason="Dual Thrust",
            source=SOURCE_TYPES.STRATEGY,
        )

    def cal(self, portfolio_info, event, *args, **kwargs):
        super(StrategyDualThrust, self).cal(portfolio_info, event)
        date_start = self.now - datetime.timedelta(days=(self._spans + 1))
        df = get_bars(event.code, date_start, self.now, as_dataframe=True)

        if df.shape[0] < self._spans + 1:
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