"""
性能: 219MB RSS, 1.86s, 3 tests [PASS]
"""

import sys
import unittest
import datetime
from time import sleep
import pandas as pd
from unittest.mock import patch, MagicMock
from ginkgo.trading.selectors.momentum_selector import MomentumSelector

engine_id = "backtest_example_001"


class MomentumSelectorTest(unittest.TestCase):
    """
    MomentumValueSelector Unit test.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(MomentumSelectorTest, self).__init__(*args, **kwargs)

    def test_init(self):
        """
        实例化 动量选择器
        """
        s = MomentumSelector(name="test_selector", window=30, rank=2)
        print(s)

    @patch("ginkgo.trading.selectors.momentum_selector.container")
    def test_pick(self, mock_container):
        """测试pick方法 - mock数据库依赖."""
        # Mock stockinfo_crud返回空DataFrame（无股票信息）
        mock_stockinfo_crud = MagicMock()
        mock_stockinfo_crud.get_all_codes.return_value = []
        mock_container.cruds.stock_info.return_value = mock_stockinfo_crud

        s = MomentumSelector(name="test_selector", window=30, rank=2)
        res = s.pick(time="2020-01-01")
        self.assertEqual(len(res), 0)

    @patch("ginkgo.trading.selectors.momentum_selector.container")
    def test_pick_batch_selects_top_n_by_momentum(self, mock_container):
        """批量查询路径：按窗口内首末收盘价正确计算动量并选出 top-N。

        数据按 timestamp 排序（模拟真实 order_by='timestamp' 查询返回）：
            A: 10→20→30  momentum = 30/10-1 = 2.0
            B: 5→50→100 momentum = 100/5-1  = 19.0  ← 最高
            C: 100→50→10 momentum = 10/100-1 = -0.9
        rank=2 期望 [B, A]。
        逐股 buggy 实现会对每个 code 用整 df 的 iloc[0]/iloc[-1]（均为 10）算出
        相同动量 0，稳定排序后得 [A, B]，与本断言不符，确保 RED 可区分。
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
        mock_si = MagicMock()
        mock_si.get_all_codes.return_value = ["A", "B", "C"]
        mock_bar = MagicMock()
        mock_bar.find.return_value.to_dataframe.return_value = df
        mock_container.cruds.stock_info.return_value = mock_si
        mock_container.cruds.bar.return_value = mock_bar

        s = MomentumSelector(name="test_selector", window=30, rank=2)
        res = s.pick(time="2020-01-01")
        self.assertEqual(res, ["B", "A"])

    @patch("ginkgo.trading.selectors.momentum_selector.container")
    def test_pick_uses_single_batch_query(self, mock_container):
        """验收：pick 只发起一次 bar 批量查询（O(1)），不再逐股 round-trip。

        旧逐股实现对 N 支股票调用 find() N 次；批量实现应只调用 1 次。
        """
        df = pd.DataFrame(
            [
                {"code": "A", "close": 10.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "B", "close": 5.0, "timestamp": pd.Timestamp("2019-12-10")},
                {"code": "A", "close": 20.0, "timestamp": pd.Timestamp("2019-12-30")},
                {"code": "B", "close": 100.0, "timestamp": pd.Timestamp("2019-12-30")},
            ]
        )
        mock_si = MagicMock()
        mock_si.get_all_codes.return_value = ["A", "B"]
        mock_bar = MagicMock()
        mock_bar.find.return_value.to_dataframe.return_value = df
        mock_container.cruds.stock_info.return_value = mock_si
        mock_container.cruds.bar.return_value = mock_bar

        s = MomentumSelector(name="test_selector", window=30, rank=2)
        s.pick(time="2020-01-01")
        self.assertEqual(
            mock_bar.find.call_count,
            1,
            "pick() 应只发起一次批量 bar 查询，而非逐股查询",
        )

    @patch("ginkgo.trading.selectors.momentum_selector.container")
    def test_pick_filters_invalid_stocks(self, mock_container):
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
        mock_si = MagicMock()
        mock_si.get_all_codes.return_value = ["Z", "X", "Y"]
        mock_bar = MagicMock()
        mock_bar.find.return_value.to_dataframe.return_value = df
        mock_container.cruds.stock_info.return_value = mock_si
        mock_container.cruds.bar.return_value = mock_bar

        s = MomentumSelector(name="test_selector", window=30, rank=2)
        res = s.pick(time="2020-01-01")
        self.assertEqual(res, ["Z"])

    def test_date_scene(self):
        pass
