"""
性能: ~220MB RSS, 2.0s, 7 tests [PASS]
"""

import unittest
import inspect
import pandas as pd
from unittest.mock import MagicMock
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.trading.selectors.momentum_selector import MomentumSelector


class MomentumSelectorTest(unittest.TestCase):
    """
    MomentumSelector Unit test.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(MomentumSelectorTest, self).__init__(*args, **kwargs)

    @staticmethod
    def _make_feeder(codes, df=None):
        """构造 mock _data_feeder（#4608：穿透已收敛到 feeder DI 注入）。"""
        feeder = MagicMock()
        feeder.get_available_codes.return_value = ServiceResult.success(data=codes)
        if df is not None:
            feeder.get_bars_window.return_value = ServiceResult.success(data=df)
        return feeder

    def test_init(self):
        """实例化 动量选择器"""
        s = MomentumSelector(name="test_selector", window=30, rank=2)
        print(s)

    def test_pick_uses_feeder_and_available_codes(self):
        """#4608：pick() 走 _data_feeder 边界，只扫有 bar 数据的 code。"""
        df = pd.DataFrame(
            [
                {"code": "A", "close": 10.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "B", "close": 5.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "A", "close": 20.0, "timestamp": pd.Timestamp("2019-12-30")},
                {"code": "B", "close": 100.0, "timestamp": pd.Timestamp("2019-12-30")},
                {"code": "NO_BAR_METADATA_ONLY", "close": 1.0, "timestamp": pd.Timestamp("2019-12-30")},
            ]
        )
        s = MomentumSelector(name="test_selector", window=30, rank=1)
        s._data_feeder = self._make_feeder(["A", "B"], df)
        res = s.pick(time="2020-01-01")

        self.assertEqual(res, ["B"])
        s._data_feeder.get_available_codes.assert_called_once()
        s._data_feeder.get_bars_window.assert_called_once()

    def test_pick_empty_universe(self):
        """universe 为空时返回空列表。"""
        s = MomentumSelector(name="test_selector", window=30, rank=2)
        s._data_feeder = self._make_feeder([])
        res = s.pick(time="2020-01-01")
        self.assertEqual(len(res), 0)

    def test_pick_batch_selects_top_n_by_momentum(self):
        """批量查询路径：按窗口内首末收盘价正确计算动量并选出 top-N。

        数据按 timestamp 排序（模拟真实查询返回）：
            A: 10→20→30  momentum = 30/10-1 = 2.0
            B: 5→50→100 momentum = 100/5-1  = 19.0  ← 最高
            C: 100→50→10 momentum = 10/100-1 = -0.9
        rank=2 期望 [B, A]。
        """
        df = pd.DataFrame(
            [
                {"code": "A", "close": 10.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "B", "close": 5.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "C", "close": 100.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "A", "close": 20.0, "timestamp": pd.Timestamp("2019-12-20")},
                {"code": "B", "close": 50.0, "timestamp": pd.Timestamp("2019-12-20")},
                {"code": "C", "close": 50.0, "timestamp": pd.Timestamp("2019-12-20")},
                {"code": "A", "close": 30.0, "timestamp": pd.Timestamp("2019-12-30")},
                {"code": "B", "close": 100.0, "timestamp": pd.Timestamp("2019-12-30")},
                {"code": "C", "close": 10.0, "timestamp": pd.Timestamp("2019-12-30")},
            ]
        )
        s = MomentumSelector(name="test_selector", window=30, rank=2)
        s._data_feeder = self._make_feeder(["A", "B", "C"], df)
        res = s.pick(time="2020-01-01")
        self.assertEqual(res, ["B", "A"])

    def test_pick_uses_single_batch_query(self):
        """验收：pick 只发起一次 bar 批量查询（O(1)），不再逐股 round-trip。"""
        df = pd.DataFrame(
            [
                {"code": "A", "close": 10.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "B", "close": 5.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "A", "close": 20.0, "timestamp": pd.Timestamp("2019-12-30")},
                {"code": "B", "close": 100.0, "timestamp": pd.Timestamp("2019-12-30")},
            ]
        )
        s = MomentumSelector(name="test_selector", window=30, rank=2)
        s._data_feeder = self._make_feeder(["A", "B"], df)
        s.pick(time="2020-01-01")
        self.assertEqual(
            s._data_feeder.get_bars_window.call_count,
            1,
            "pick() 应只通过 _data_feeder 发起一次批量 bar 查询，而非逐股查询",
        )

    def test_pick_filters_invalid_stocks(self):
        """过滤无效股票：窗口内不足两条 bar 或首条收盘价非正的股票不参与排名。

            Z: 10→20      count=2, first=10  → 有效，momentum=1.0
            X: 15         count=1           → 不足两条，剔除
            Y: 0→10       count=2, first=0  → 首条非正，剔除
        rank=2 但仅 Z 有效 → 期望 ['Z']。
        """
        df = pd.DataFrame(
            [
                {"code": "Z", "close": 10.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "X", "close": 15.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "Y", "close": 0.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "Z", "close": 20.0, "timestamp": pd.Timestamp("2019-12-30")},
                {"code": "Y", "close": 10.0, "timestamp": pd.Timestamp("2019-12-30")},
            ]
        )
        s = MomentumSelector(name="test_selector", window=30, rank=2)
        s._data_feeder = self._make_feeder(["Z", "X", "Y"], df)
        res = s.pick(time="2020-01-01")
        self.assertEqual(res, ["Z"])

    def test_no_container_import(self):
        """#4608：MomentumSelector 不再穿透 container（依赖收敛到 _data_feeder DI）。"""
        from ginkgo.trading.selectors import momentum_selector
        src = inspect.getsource(momentum_selector)
        self.assertNotIn(
            "from ginkgo.data.containers",
            src,
            "MomentumSelector 不应 import container，应通过 _data_feeder 取数据",
        )

    def test_pick_no_feeder_skips_with_warning(self):
        """#4608：_data_feeder 未绑定时 WARN + 返回空 _interested，不崩。"""
        s = MomentumSelector(name="test_selector", window=30, rank=2)
        # _data_feeder 默认 None（未 bind）
        res = s.pick(time="2020-01-01")
        self.assertEqual(res, [])

    def test_date_scene(self):
        pass


if __name__ == "__main__":
    unittest.main()
