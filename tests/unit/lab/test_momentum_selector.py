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

    def test_date_scene(self):
        pass
