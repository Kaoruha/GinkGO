"""
ADR-010 收尾回归：momentum/popularity selector 删除 hasattr(bars, 'to_dataframe') 死分支。

- BaseCRUD.find 恒返 ModelList（必带 to_dataframe），原 else 是死代码。
- 验证：非空 bars 走 to_dataframe 正常产出；空 bars 走 continue。
- 关键：bars 为 MagicMock（无真实 to_dataframe 属性时会触发 AttributeError 证明旧 else
  分支已删——这里 mock 给出 to_dataframe，确保新代码直接调用，不再走鸭子探测）。
"""

import datetime
import unittest
from unittest.mock import patch, MagicMock

import pandas as pd

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.trading.selectors.momentum_selector import MomentumSelector
from ginkgo.trading.selectors.popularity_selector import PopularitySelector


def _make_bars(df: pd.DataFrame):
    """构造一个满足 selector 守卫的 mock bars：支持 len() / bool() / to_dataframe()。"""
    bars = MagicMock()
    bars.__bool__ = MagicMock(return_value=len(df) > 0)
    bars.__len__ = MagicMock(return_value=len(df))
    bars.to_dataframe.return_value = df
    return bars


class MomentumSelectorHasattrRemovalTest(unittest.TestCase):
    @patch("ginkgo.trading.selectors.momentum_selector.container")
    def test_non_empty_bars_uses_service_dataframe(self, mock_container):
        """非空 bars：消费 service 的 DataFrame 出口，按 momentum 排序产出 code。

        批量实现（#4650）按 code 列 groupby，故 df 需含真实 bar 的 code/timestamp 列
        （旧逐股实现 code 来自循环变量，fixture 曾省略 code 列）。
        """
        df = pd.DataFrame(
            {
                "code": ["000001", "000001"],
                "close": [10.0, 12.0],
                "volume": [100, 200],
                "timestamp": [pd.Timestamp("2020-05-01"), pd.Timestamp("2020-05-31")],
            }
        )
        mock_bar_service = MagicMock()
        mock_bar_service.get_available_codes.return_value = ServiceResult.success(data=["000001"])
        mock_bar_service.get_bars_df.return_value = ServiceResult.success(data=df)
        mock_container.bar_service.return_value = mock_bar_service

        s = MomentumSelector(name="t", window=30, rank=2)
        res = s.pick(time=datetime.datetime(2020, 6, 1))
        self.assertEqual(res, ["000001"])
        mock_bar_service.get_bars_df.assert_called_once()

    @patch("ginkgo.trading.selectors.momentum_selector.container")
    def test_empty_bars_continues(self, mock_container):
        """空 bars：DataFrame 空结果短路。"""
        mock_bar_service = MagicMock()
        mock_bar_service.get_available_codes.return_value = ServiceResult.success(data=["000001"])
        mock_bar_service.get_bars_df.return_value = ServiceResult.success(data=pd.DataFrame())
        mock_container.bar_service.return_value = mock_bar_service

        s = MomentumSelector(name="t", window=30, rank=2)
        res = s.pick(time=datetime.datetime(2020, 6, 1))
        self.assertEqual(res, [])
        mock_bar_service.get_bars_df.assert_called_once()


class PopularitySelectorHasattrRemovalTest(unittest.TestCase):
    @patch("ginkgo.trading.selectors.popularity_selector.container")
    def test_non_empty_bars_uses_to_dataframe(self, mock_container):
        """非空 bars：直接调 to_dataframe，按 sum_volume 排序产出 code。"""
        mock_stockinfo = MagicMock()
        mock_stockinfo.get_all_codes.return_value = ["000001"]
        mock_container.cruds.stock_info.return_value = mock_stockinfo

        df = pd.DataFrame({"close": [10.0, 11.0], "volume": [500, 700]})
        mock_bar = MagicMock()
        mock_bar.find.return_value = _make_bars(df)
        mock_container.cruds.bar.return_value = mock_bar

        s = PopularitySelector(name="t", rank=5, span=10)
        s.current_timestamp = datetime.datetime(2020, 6, 1)
        s._last_pick = None
        res = s.pick()
        self.assertEqual(res, ["000001"])
        mock_bar.find.return_value.to_dataframe.assert_called_once()

    @patch("ginkgo.trading.selectors.popularity_selector.container")
    def test_empty_bars_continues(self, mock_container):
        """空 bars：len == 0 守卫触发 continue，不调 to_dataframe。"""
        mock_stockinfo = MagicMock()
        mock_stockinfo.get_all_codes.return_value = ["000001"]
        mock_container.cruds.stock_info.return_value = mock_stockinfo

        mock_bar = MagicMock()
        mock_bar.find.return_value = _make_bars(pd.DataFrame())
        mock_container.cruds.bar.return_value = mock_bar

        s = PopularitySelector(name="t", rank=5, span=10)
        s.current_timestamp = datetime.datetime(2020, 6, 1)
        s._last_pick = None
        res = s.pick()
        self.assertEqual(res, [])
        mock_bar.find.return_value.to_dataframe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
