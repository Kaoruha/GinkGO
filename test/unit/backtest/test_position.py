import unittest
from decimal import Decimal
import random
import pandas as pd
from ginkgo.backtest.entities.position import Position
from ginkgo.libs import to_decimal


class TestPosition(unittest.TestCase):
    def setUp(self):
        """
        创建多个随机参数的 Position 实例，用于测试多样化场景。
        """
        self.positions = []
        for i in range(5):
            cost = random.uniform(1, 100)
            price = random.uniform(1, 100)
            volume = random.randint(1, 1000)
            frozen_volume = random.randint(0, volume)
            frozen_money = frozen_volume * price
            fee = random.uniform(0, 10)
            pos = Position(
                portfolio_id=f"portfolio_{i}",
                engine_id=f"engine_{i}",
                code=f"00000{i}",
                cost=cost,
                volume=volume,
                frozen_volume=frozen_volume,
                frozen_money=frozen_money,
                price=price,
                fee=fee,
                uuid=f"uuid_{i}",
            )
            self.positions.append(pos)

    def test_initialization_random(self):
        """
        测试多个 Position 随机实例初始化的有效性。
        """
        for pos in self.positions:
            self.assertIsInstance(pos.volume, int)
            self.assertIsInstance(pos.frozen_money, Decimal)
            self.assertTrue(0 <= pos.frozen_volume <= pos.volume)
            self.assertGreaterEqual(pos.cost, 0)
            self.assertGreaterEqual(pos.price, 0)

    def test_update_worth_random(self):
        """
        测试多个实例的 update_worth 方法是否正确计算市值。
        """
        for pos in self.positions:
            pos.update_worth()
            expected = round((pos.volume + pos.frozen_volume) * pos.price, 2)
            self.assertEqual(pos.worth, expected)

    def test_update_profit_random(self):
        """
        测试多个实例的 update_profit 方法是否正确计算盈亏。
        """
        for pos in self.positions:
            pos.update_profit()
            expected = (pos.volume + pos.frozen_volume) * (pos.price - pos.cost) - pos.fee
            self.assertEqual(pos.profit, expected)

    def test_set_from_series_random(self):
        """
        测试 set 方法是否可以正确地从 Series 中导入随机属性。
        """
        for i, pos in enumerate(self.positions):
            data = pd.Series(
                {
                    "portfolio_id": f"new_portfolio_{i}",
                    "engine_id": f"new_engine_{i}",
                    "code": f"99999{i}",
                    "cost": 55.5,
                    "volume": 500,
                    "frozen_volume": 100,
                    "frozen_money": 3000.0,
                    "price": 66.6,
                    "fee": 2.5,
                    "uuid": f"new_uuid_{i}",
                }
            )
            pos.set(data)
            self.assertEqual(pos.portfolio_id, f"new_portfolio_{i}")
            self.assertEqual(pos.engine_id, f"new_engine_{i}")
            self.assertEqual(pos.code, f"99999{i}")
            self.assertEqual(pos.volume, 500)
            self.assertEqual(pos.frozen_volume, 100)
            self.assertEqual(pos.frozen_money, Decimal("3000.0"))
            self.assertEqual(pos.price, Decimal("66.6"))
            self.assertEqual(pos.cost, Decimal("55.5"))
            self.assertEqual(pos.fee, Decimal("2.5"))
            self.assertEqual(pos._uuid, f"new_uuid_{i}")

    def test_freeze_unfreeze_random(self):
        """
        测试冻结和解冻逻辑是否能在多个实例中正确运行。
        """
        for pos in self.positions:
            freeze_amount = min(pos.volume, 10)
            result = pos.freeze(freeze_amount)
            self.assertTrue(result)
            self.assertEqual(pos.volume, pos._volume)
            self.assertEqual(pos.frozen_volume, pos._frozen_volume)

            unfreeze_amount = min(pos.frozen_volume, 5)
            pos.unfreeze(unfreeze_amount)
            self.assertEqual(pos.frozen_volume, pos._frozen_volume)
            self.assertEqual(pos.volume, pos._volume)

    def test_add_fee_random(self):
        """
        测试 add_fee 是否正确累计手续费。
        """
        for pos in self.positions:
            before_fee = pos.fee
            delta_fee = Decimal("1.23")
            pos.add_fee(delta_fee)
            self.assertEqual(pos.fee, before_fee + delta_fee)

    def test_bought_random(self):
        """
        测试 _bought 方法是否正确调整 volume 和成本。
        """
        for pos in self.positions:
            buy_price = Decimal("10.0")
            buy_volume = 100
            old_volume = pos.volume
            old_cost = pos.cost
            result = pos._bought(buy_price, buy_volume)
            self.assertTrue(result)
            self.assertEqual(pos.volume, old_volume + buy_volume)
            expected_cost = ((old_cost * old_volume + buy_price * buy_volume) / (old_volume + buy_volume)).quantize(
                Decimal("0.0001")
            )
            self.assertEqual(pos.cost.quantize(Decimal("0.0001")), expected_cost)

    def test_sold_random(self):
        """
        测试 _sold 是否能从已冻结部分卖出。
        """
        for pos in self.positions:
            pos._frozen_volume = 50
            result = pos._sold(Decimal("9.0"), 30)
            self.assertTrue(result)
            self.assertEqual(pos.frozen_volume, 20)
