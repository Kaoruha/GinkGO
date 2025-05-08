import unittest
from decimal import Decimal
import pandas as pd

from ginkgo.backtest.matchmakings.base_matchmaking import MatchMakingBase


class DummyEvent:
    def __init__(self, name="dummy"):
        self.name = name


class TestMatchMakingBase(unittest.TestCase):
    def setUp(self):
        self.matchmaker = MatchMakingBase()

    def test_initial_state(self):
        self.assertEqual(self.matchmaker.name, "HaloMatchmaking")
        self.assertIsInstance(self.matchmaker.price_cache, pd.DataFrame)
        self.assertEqual(self.matchmaker.order_book, {})
        self.assertEqual(self.matchmaker.commission_rate, Decimal("0.0003"))
        self.assertEqual(self.matchmaker.commission_min, 5)

    def test_cal_fee_long(self):
        fee = self.matchmaker.cal_fee(100000, is_long=True)
        # 手工算一下费率
        # transfer: 1, collection: 6.87, commission: 30 > 5 -> total = 37.87
        expected = Decimal("1") + Decimal("6.87") + Decimal("30")  # no stamp tax
        self.assertEqual(fee, round(expected, 2))

    def test_cal_fee_short(self):
        fee = self.matchmaker.cal_fee(100000, is_long=False)
        # stamp: 100, transfer: 1, collection: 6.87, commission: 30 -> total = 137.87
        expected = Decimal("100") + Decimal("1") + Decimal("6.87") + Decimal("30")
        self.assertEqual(fee, round(expected, 2))

    def test_cal_fee_minimum_commission(self):
        # transaction too small, commission < min
        fee = self.matchmaker.cal_fee(1000, is_long=True)
        # commission = 0.3 < 5 -> use 5
        # stamp: 0, transfer: 0.01, collection: 0.0687, commission: 5 -> 5.08
        expected = Decimal("0.01") + Decimal("0.0687") + Decimal("5")
        self.assertEqual(fee, round(expected, 2))

    def test_cal_fee_invalid(self):
        fee = self.matchmaker.cal_fee(-100, is_long=True)
        self.assertEqual(fee, 0)

    def test_put_event_without_engine(self):
        mm = MatchMakingBase()
        mm._engine_put = None
        # just make sure it doesn't crash
        mm.put(DummyEvent())

    def test_on_time_goes_by(self):
        self.matchmaker._price_cache = pd.DataFrame({"a": [1, 2, 3]})
        self.matchmaker._order_book = {"AAPL": ["order1", "order2"]}
        self.matchmaker.on_time_goes_by("2023-01-01")
        self.assertTrue(self.matchmaker.price_cache.empty)
        self.assertEqual(self.matchmaker.order_book, {})
