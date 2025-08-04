import sys
import unittest
import datetime
from time import sleep
import pandas as pd
from ginkgo.data import *
from ginkgo.backtest.selectors import MomentumSelector

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

    def test_pick(self):
        s = MomentumSelector(name="test_selector", window=30, rank=2)
        res = s.pick(time="2020-01-01")
        self.assertEqual(len(res), 2)

    def test_date_scene(self):
        pass
