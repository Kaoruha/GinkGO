"""
Author: Kaoru
Date: 2022-03-21 17:06:32
LastEditTime: 2022-03-23 10:30:59
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/test/test_position.py
What goes around comes around.
"""
from re import I
from sqlite3 import paramstyle
from typing import Tuple
import unittest
from src.backtest.postion import Position
from src.backtest.sizer.base_sizer import BaseSizer


class PositionTest(unittest.TestCase):
    """
    持仓类单元测试
    """

    def __init__(self, *args, **kwargs):
        super(PositionTest, self).__init__(*args, **kwargs)
        self.code = "test_01"
        self.name = "test_position"
        self.price = 10.0
        self.volume = 10000
