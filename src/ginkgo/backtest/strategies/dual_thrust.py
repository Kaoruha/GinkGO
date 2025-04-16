import time
import datetime
from ginkgo.backtest.events import EventSignalGeneration
from ginkgo.backtest.signal import Signal
from ginkgo.backtest.strategies.base_strategy import StrategyBase
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars


class StrategyDualThrust(StrategyBase):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self, name: str = "DualThrust", spans: str = "7", k_buy: str = "0.5", k_sell: str = "0.5", *args, **kwargs
    ):
        super(StrategyVolumeActivate, self).__init__(name, *args, **kwargs)
        self._spans = int(spans)
        self._k_buy = Decimal(k_buy)
        self._k_sell = Decimal(k_sell)
        self.win = 0
        self.loss = 0

    def cal(self, portfolio_info, event, *args, **kwargs):
        super(StrategyVolumeActivate, self).cal(portfolio_info, event)
        date_start = self.now + datetime.timedelta(days=-(self._spans + 1))
        date_end = self.now
        df = get_bars(event.code, date_start, date_end, as_dataframe=True)
        if df.shape[0] == 0:
            # No data , wait for next chance.
            return
        if df.shape[0] < self._spans + 1:
            # No enough data. wait for next chance.
            return
        today_hh = df["high"].rolling(window=self._spans).max()
        today_lc = df["close"].rolling(window=self._spans).min()
        today_hc = df["close"].rolling(window=self._spans).max()
        today_ll = df["low"].rolling(window=self._spans).min()
        today_r = max(today_hh - today_lc, today_hc - today_ll)
        today_buy_line = df.iloc[-1, "open"] + self._k_buy * today_r
        today_sell_line = df.iloc[-1, "open"] + self._k_sell * today_r

        last_hh = df.iloc[-2, "high"].rolling(window=self._spans).max()
        last_lc = df.iloc[-2, "close"].rolling(window=self._spans).min()
        last_hc = df.iloc[-2, "close"].rolling(window=self._spans).max()
        last_ll = df.iloc[-2, "low"].rolling(window=self._spans).min()
        last_r = max(last_hh - last_lc, last_hc - last_ll)
        last_buy_line = df.iloc[-2, "open"] + self._k_buy * last_r
        last_sell_line = df.iloc[-2, "open"] + self._k_sell * last_r
        if df.iloc[-2, "close"] < last_buy_line and df.iloc[-1, "close"] > today_buy_line:
            if event.code in portfolio_info["positions"].keys():
                return
            self.log("INFO", f"Gen Long Signal about {code} from {self.name}")
            s = Signal(
                portfolio_id=portfolio_info["uuid"],
                engine_id=self.engine_id,
                timestamp=portfolio_info["now"],
                code=code,
                direction=DIRECTION_TYPES.LONG,
                reason="Dual Thrust",
                source=SOURCE_TYPES.STRATEGY,
            )
            return signal
        if df.iloc[-2, "close"] > last_sell_line and df.iloc[-1, "close"] < today_sell_line:
            if event.code not in portfolio_info["positions"].keys():
                return
            self.log("INFO", f"Gen Short Signal about {code} from {self.name}")
            s = Signal(
                portfolio_id=portfolio_info["uuid"],
                engine_id=self.engine_id,
                timestamp=portfolio_info["now"],
                code=code,
                direction=DIRECTION_TYPES.SHORT,
                reason="Dual Thrust",
                source=SOURCE_TYPES.STRATEGY,
            )
            return signal
