# Upstream: EngineAssemblyService, PortfolioBase
# Downstream: BaseSelector, container, GLOG
# Role: 热度选股器，基于历史交易数据统计选取最活跃的Top-N股票

import datetime
from rich.progress import Progress

from ginkgo.trading.bases.selector_base import SelectorBase as BaseSelector
from ginkgo.data.containers import container
from ginkgo.libs import GLOG

# 热度统计窗口上限（日历日）。与 MomentumSelector.MAX_WINDOW 对齐：业务 ≤1 年，
# 技术上防止未来改批量查询后一次取全表 OOM（当前逐股路径有 page_size=span+10 兜底，
# 但参数校验是更上游、更稳的防御）。
MAX_SPAN = 365


class PopularitySelector(BaseSelector):
    __abstract__ = False

    def __init__(
        self,
        name: str = "PopularitySelector",
        rank: int = 10,
        span: int = 30,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(name, *args, **kwargs)
        # 源头校验：span 必须为 [1, MAX_SPAN] 内 int。与 MomentumSelector 同款防御。
        if isinstance(span, bool) or not isinstance(span, int) or not (1 <= span <= MAX_SPAN):
            raise ValueError(
                f"span must be int in [1, {MAX_SPAN}], got {span!r}"
            )
        self.rank = rank
        self.span = span
        self._interested = []
        self.interval = 10
        self._last_pick = None

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        if self.current_timestamp is None:
            GLOG.ERROR("No date set. skip picking.")
            return []

        if self._last_pick is None:
            self._last_pick = self.current_timestamp

        if self.current_timestamp - self._last_pick < datetime.timedelta(days=self.interval):
            if len(self._interested) > 0:
                return self._interested
        else:
            self._last_pick = self.current_timestamp

        if self.current_timestamp is None:
            GLOG.ERROR("No date set. skip picking.")
            return self._interested

        stockinfo_crud = container.cruds.stock_info()
        codes = stockinfo_crud.get_all_codes()
        if not codes:
            return self._interested

        date_start = self.current_timestamp + datetime.timedelta(days=int(self.span * -1))
        bar_crud = container.cruds.bar()

        GLOG.INFO(f"PopularitySelector: scanning {len(codes)} stocks, span={self.span}d")

        results = []
        with Progress() as progress:
            task = progress.add_task("Popularity scan", total=len(codes))
            for code in codes:
                progress.update(task, advance=1, description=f"Scanning {code}")
                try:
                    bars = bar_crud.find(
                        filters={"code": code, "timestamp__gte": date_start, "timestamp__lte": self.current_timestamp},
                        page_size=self.span + 10,
                    )
                    if not bars or len(bars) == 0:
                        continue
                    df = bars.to_dataframe()
                    if df is None or df.empty:
                        continue
                    total_volume = float(df["volume"].sum())
                    if total_volume > 0:
                        results.append({"code": code, "sum_volume": total_volume})
                except Exception:
                    continue

        if not results:
            return self._interested

        import pandas as pd
        res = pd.DataFrame(results).sort_values(by="sum_volume", ascending=False)

        if abs(self.rank) > len(res):
            self.rank = len(res) if self.rank > 0 else -len(res)

        if self.rank > 0:
            res = res.head(abs(self.rank))
        else:
            res = res.tail(abs(self.rank))

        self._interested = res["code"].tolist()
        GLOG.INFO(f"PopularitySelector: picked {len(self._interested)} stocks")
        return self._interested
