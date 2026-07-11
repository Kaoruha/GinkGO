# Upstream: Backtest Engines (调用cal方法)
# Downstream: BaseStrategy, IDataFeeder, DIRECTION_TYPES
# Role: Dual Thrust策略 — 通过 data_feeder 获取历史K线计算突破区间






import datetime
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
        self._k_buy = float(k_buy)
        self._k_sell = float(k_sell)

    def _calculate_range(self, df: pd.DataFrame) -> float:
        """
        Calculates the range for the Dual Thrust strategy.
        """
        hh = df["high"].rolling(window=self._spans).max().iloc[-1]
        lc = df["close"].rolling(window=self._spans).min().iloc[-1]
        hc = df["close"].rolling(window=self._spans).max().iloc[-1]
        ll = df["low"].rolling(window=self._spans).min().iloc[-1]
        # #4708: ClickHouse bar 列为 Decimal，max()/加减结果保留 Decimal；
        # cal() 的 `open + k_buy * r`（float 系数）会触发 Decimal+float TypeError。
        # 末尾 float() 归一，使本方法在 float / Decimal 列下都返回 float。
        return float(max(hh - lc, hc - ll))

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
        now = portfolio_info.get("now")
        if now is None:
            return []
        # #4658: 按交易日倍数预留日历日窗口。A 股每周 2/7 非交易 + 法定节假日，
        # spans+1 日历日仅约 (spans+1)*5/7 交易日 < spans+1，触发下方 df.shape[0]
        # 守卫恒真 → 策略 100% 零信号。spans*2+5 覆盖周末与节假日 buffer，
        # 多取的历史行被 _calculate_range 的 rolling(window=spans).iloc[-1] 自然忽略。
        date_start = now - datetime.timedelta(days=(self._spans * 2 + 5))
        df = self.data_feeder.get_historical_data(
            symbols=[event.code], start_time=date_start,
            end_time=now, data_type="bar"
        )

        if df is None or df.empty or df.shape[0] < self._spans + 1:
            return []

        today_r = self._calculate_range(df)
        # #4708: Decimal 列下 df.iloc[-1]["open"] 是 Decimal，与 float 系数算术抛
        # TypeError；显式 float() 归一（与 _calculate_range 返回类型一致）。
        today_open = float(df.iloc[-1]["open"])
        today_buy_line = today_open + self._k_buy * today_r
        today_sell_line = today_open - self._k_sell * today_r

        last_r = self._calculate_range(df.iloc[:-1])
        last_open = float(df.iloc[-2]["open"])
        last_buy_line = last_open + self._k_buy * last_r
        last_sell_line = last_open - self._k_sell * last_r

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