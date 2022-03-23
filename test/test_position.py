"""
Author: Kaoru
Date: 2022-03-21 17:06:32
LastEditTime: 2022-03-23 10:30:59
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/test/test_position.py
What goes around comes around.
"""
import unittest
from src.backtest.postion import Position
from src.libs import GINKGOLOGGER as gl


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
        self.date = "2000-01-01"

    def reset(self) -> Position:
        p = Position(
            code=self.code,
            name=self.name,
            cost=self.price,
            volume=self.volume,
            datetime=self.date,
        )
        return p

    def test_PositionInit_OK(self):
        gl.logger.critical("开始Position初始化测试.")
        p = self.reset()

        self.assertEqual(
            first={
                "code": self.code,
                "name": self.name,
                "cost": self.price,
                "volume": self.volume,
                "ava": 0,
                "sellf": 0,
                "t1f": self.volume,
                "volume": self.volume,
                "value": self.price * self.volume,
            },
            second={
                "code": p.code,
                "name": p.name,
                "cost": p.cost,
                "volume": p.volume,
                "ava": p.avaliable_volume,
                "sellf": p.frozen_sell,
                "t1f": p.frozen_t1,
                "volume": p.volume,
                "value": p.market_value,
            },
        )

        gl.logger.critical("Position初始化测试完成.")

    def test_PositionUpdatePrice_OK(self):
        gl.logger.critical("开始Position价格信息更新测试.")
        p = self.reset()
        param = [
            (12, "2020-02-02"),
            (11, "2020-02-01"),
        ]
        for i in param:
            gl.logger.debug(f"{i[1]} 更新价格 {i[0]}.")
            gl.logger.debug(p)
            p.update_last_price(price=i[0], datetime=i[1])
            self.assertEqual(
                first={"lp": i[0], "dt": i[1], "value": i[0] * self.volume},
                second={
                    "lp": p.last_price,
                    "dt": p.datetime.strftime("%Y-%m-%d"),
                    "value": p.market_value,
                },
            )
        gl.logger.critical("Position价格信息更新测试完成.")

    def test_PositionUnfreezeT1_OK(self):
        pass

    def test_PositionBuy_OK(self):
        pass

    def test_PositionFreezeSell_OK(self):
        pass

    def test_PositionPreSell_OK(self):
        pass

    def test_PositionSell_OK(self):
        pass

    def test_PositionUpdate(self):
        pass
