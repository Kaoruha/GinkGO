"""
业绩基准
"""

import pandas as pd
from ginkgo.backtest.analyzer.base_analyzer import BaseAnalyzer
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm


class BenchMark(BaseAnalyzer):
    def __init__(self, name="业绩基准", target="sh.000001"):
        super().__init__(name=name)
        self.target = target  # TODO 要加上校验
        self.raw = pd.DataFrame(columns=("datetime", self.target, "portfolio"))

    def __repr__(self) -> str:
        r = f"{self.name}, 标的: {self.target}"
        return r

    def record(self, timestamp, *args, **kwargs):
        t = timestamp
        target = gm.get_dayBar_by_mongo(code=self.target, start_date=t, end_date=t).loc[
            0
        ]
        # TODO 回测可以考虑缓存数据
        value = kwargs["broker"].total_capital
        self.raw = self.raw.append(
            {"datetime": t, self.target: float(target.close), "portfolio": value},
            ignore_index=True,
        )

    def report(self, *args, **kwargs):
        # 1. 排序
        # 2. 如果排序结果与原数据有出入，则跑出警告，回测应该有误
        # 3. 返回
        r = {}
        r["name"] = "benchmark:" + self.target
        return r
