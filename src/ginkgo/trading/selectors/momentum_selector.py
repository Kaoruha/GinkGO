# Upstream: EngineAssemblyService, PortfolioBase
# Downstream: BaseSelector, container, pandas, GLOG
# Role: 动量选股器，基于时间窗口内的收益率排名动态选取Top-N股票

from ginkgo.trading.bases.selector_base import SelectorBase as BaseSelector
from ginkgo.data.containers import container
from ginkgo.libs import datetime_normalize, GLOG
import datetime

# 动量回看窗口上限（日历日）。业务上动量语义 ≤1 年；技术上防止批量 bar 查询
# 一次取全表（master 库 5423 code × 35 年 ≈ 1568 万行）导致 OOM/卡死。
MAX_WINDOW = 365


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
        # 源头校验：window 必须为 [1, MAX_WINDOW] 内 int，避免 timedelta(days=) 语义错
        # 或批量查询取全表 OOM。bool 是 int 子类，一并拒绝。
        if isinstance(window, bool) or not isinstance(window, int) or not (1 <= window <= MAX_WINDOW):
            raise ValueError(
                f"window must be int in [1, {MAX_WINDOW}], got {window!r}"
            )
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

        # 批量查询：一次取全市场窗口内全部 bar，内存 groupby 算动量。
        # 将 DB 查询次数从 O(universe) 降到 O(1)，避免逐股 round-trip。
        bar_crud = container.cruds.bar()
        bars = bar_crud.find(
            filters={"timestamp__gte": start_date, "timestamp__lte": end_date},
            order_by="timestamp",
        )
        # 空结果短路：ModelList 实现 __bool__/__len__，空时不调 to_dataframe。
        if not bars:
            return self._interested
        df = bars.to_dataframe()
        if df is None or df.empty:
            return self._interested

        # 按 (code, timestamp) 排序，确保每组 first/last 为窗口内最早/最新收盘价，
        # 不依赖 DB 隐式排序（原逐股版未指定 order_by，属脆弱行为，此处一并修正）。
        valid_codes = set(codes)
        df = df.sort_values(["code", "timestamp"])
        grouped = (
            df[df["code"].isin(valid_codes)]
            .groupby("code")["close"]
            .agg(["first", "last", "count"])
        )
        # 过滤无效股票：窗口内不足两条 bar，或首条收盘价非正（动量无意义/除零）。
        grouped = grouped[(grouped["count"] >= 2) & (grouped["first"] > 0)]
        if grouped.empty:
            return self._interested

        grouped["momentum"] = grouped["last"] / grouped["first"] - 1
        top = grouped.sort_values("momentum", ascending=False).head(self._rank)
        self._interested = top.index.tolist()
        GLOG.INFO(f"MomentumSelector: picked {len(self._interested)} stocks: {self._interested[:5]}")
        return self._interested
