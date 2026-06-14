# Upstream: EngineAssemblyService, PortfolioBase
# Downstream: BaseSelector, container, pandas, GLOG
# Role: 动量选股器，基于时间窗口内的收益率排名动态选取Top-N股票

from ginkgo.trading.bases.selector_base import SelectorBase as BaseSelector
from ginkgo.data.containers import container
from ginkgo.libs import datetime_normalize, GLOG
import pandas as pd
import datetime


class MomentumSelector(BaseSelector):
    __abstract__ = False

    def __init__(
        self,
        name: str = "MomentumSelector",
        interval: int = 5,
        rank: int = 5,
        window: int = 20,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(name, *args, **kwargs)
        self._interested = []
        self._interval = interval
        self._rank = rank
        self._window = window
        self._last_pick = None

    @property
    def interval(self) -> int:
        return self._interval

    @property
    def rank(self) -> int:
        return self._rank

    @property
    def window(self) -> int:
        return self._window

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        end_date = datetime_normalize(time)
        start_date = end_date - datetime.timedelta(days=self._window)

        if self._last_pick is None:
            self._last_pick = end_date
        else:
            if end_date < self._last_pick:
                self._last_pick = end_date
            if end_date - datetime_normalize(self._last_pick) <= datetime.timedelta(days=self._interval):
                if len(self._interested) > 0:
                    return self._interested
            if end_date - datetime_normalize(self._last_pick) > datetime.timedelta(days=self._interval):
                self._last_pick = end_date

        # Get all stock codes instead of just 50
        stockinfo_crud = container.cruds.stock_info()
        codes = stockinfo_crud.get_all_codes()
        if not codes:
            return self._interested

        GLOG.INFO(f"MomentumSelector: scanning {len(codes)} stocks, window={self._window}d, top={self._rank}")

        results = []
        bar_crud = container.cruds.bar()
        for code in codes:
            try:
                bars = bar_crud.find(
                    filters={"code": code, "timestamp__gte": start_date, "timestamp__lte": end_date},
                    page_size=self._window + 5,
                )
                if not bars or len(bars) < 2:
                    continue
                df = bars.to_dataframe()
                if df.empty or len(df) < 2:
                    continue
                first_close = float(df["close"].iloc[0])
                last_close = float(df["close"].iloc[-1])
                if first_close <= 0:
                    continue
                momentum = last_close / first_close - 1
                results.append({"code": code, "momentum": momentum})
            except Exception:
                continue

        if not results:
            return self._interested

        res = pd.DataFrame(results).sort_values(by="momentum", ascending=False).head(self._rank)
        self._interested = res["code"].tolist()
        GLOG.INFO(f"MomentumSelector: picked {len(self._interested)} stocks: {self._interested[:5]}")
        return self._interested
