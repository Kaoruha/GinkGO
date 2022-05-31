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
            price=self.price,
            volume=self.volume,
            datetime=self.date,
        )
        return p

    def test_PositionInit_OK(self):
        print("")
        gl.logger.critical("Position初始化测试开始.")
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
        print("")
        gl.logger.critical("Position价格信息更新测试开始.")
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
                first={
                    "lastprice": i[0],
                    "datetime": i[1],
                    "value": i[0] * self.volume,
                },
                second={
                    "lastprice": p.last_price,
                    "datetime": p.datetime.strftime("%Y-%m-%d"),
                    "value": p.market_value,
                },
            )
        gl.logger.critical("Position价格信息更新测试完成.")

    def test_PositionUnfreezeT1_OK(self):
        print("")
        gl.logger.critical("Position解除T+1冻结测试开始.")
        p = self.reset()
        p.unfreeze_t1()
        self.assertEqual(
            first={
                "lastprice": self.price,
                "volume": self.volume,
                "ava": self.volume,
                "frozent1": 0,
                "frozensell": 0,
            },
            second={
                "lastprice": p.last_price,
                "volume": p.volume,
                "ava": p.avaliable_volume,
                "frozent1": p.frozen_t1,
                "frozensell": p.frozen_sell,
            },
        )
        gl.logger.critical("Position解除T+1冻结测试完成.")

    def test_PositionBuy_OK(self):
        print("")
        gl.logger.critical("Position新开多头仓位测试开始.")
        p = self.reset()
        p.unfreeze_t1()
        self.assertEqual(
            first={
                "code": self.code,
                "name": self.name,
                "cost": self.price,
                "lastprice": self.price,
                "volume": self.volume,
                "frozensell": 0,
                "frozent1": 0,
                "frozen": 0,
                "float_profit": 0.0,
                "avaliable": self.volume,
                "datetime": self.date,
            },
            second={
                "code": p.code,
                "name": p.name,
                "cost": p.cost,
                "lastprice": p.last_price,
                "volume": p.volume,
                "frozensell": p.frozen_sell,
                "frozent1": p.frozen_t1,
                "frozen": p.frozen,
                "float_profit": p.float_profit,
                "avaliable": p.avaliable_volume,
                "datetime": p.datetime.strftime("%Y-%m-%d"),
            },
        )
        param = [
            # 0price, 1volume, 2date, 3cost, 4totalvolume, 5ava, 6frozensell, 7frozent1
            (10, 10000, "2020-01-01", 10, 20000, 10000, 0, 10000),
            (10, 10000, "2020-01-01", 10, 30000, 10000, 0, 20000),
            (10, 10000, "2020-01-02", 10, 40000, 10000, 0, 30000),
            (12, 40000, "2020-01-02", 11, 80000, 10000, 0, 70000),
            (20, 80000, "2020-01-03", 15.5, 160000, 10000, 0, 150000),
        ]
        for i in param:
            p._Position__buy(volume=i[1], price=i[0], datetime=i[2])
            self.assertEqual(
                first={
                    "cost": i[3],
                    "volume": i[4],
                    "ava": i[5],
                    "frozensell": i[6],
                    "frozent1": i[7],
                },
                second={
                    "cost": p.cost,
                    "volume": p.volume,
                    "ava": p.avaliable_volume,
                    "frozensell": p.frozen_sell,
                    "frozent1": p.frozen_t1,
                },
            )

        gl.logger.critical("Position新开多头仓位测试完成.")

    def test_PositionFreezePosition_OK(self):
        print("")
        gl.logger.critical("Position冻结仓位测试开始.")
        p = self.reset()
        p.unfreeze_t1()
        param = [
            # 0sellvolume, 1frozensell, 2avaliable, 3value
            (5000, 5000, 5000, 100000),
            (1000, 6000, 4000, 100000),
            (1000, 7000, 3000, 100000),
            (1000, 8000, 2000, 100000),
        ]
        for i in param:
            p.freeze_position(volume=i[0])
            self.assertEqual(
                first={"frozensell": i[1], "ava": i[2], "totalvalue": i[3]},
                second={
                    "frozensell": p.frozen_sell,
                    "ava": p.avaliable_volume,
                    "totalvalue": p.market_value,
                },
            )

        gl.logger.critical("Position冻结仓位测试完成.")

    def test_PositionSell_OK(self):
        print("")
        gl.logger.critical("Position卖出测试开始.")
        p = self.reset()
        p.unfreeze_t1()
        param = [
            # 0presell, 1selldone, 2frozensell, 3ava, 4total
            (5000, 1000, 4000, 5000, 90000),
            (0, 1000, 3000, 5000, 80000),
            (0, 3000, 0, 5000, 50000),
            (5000, 5000, 0, 0, 0),
        ]
        for i in param:
            p.freeze_position(i[0])
            p._Position__sell(i[1])
            self.assertEqual(
                first={"frozensell": i[2], "ava": i[3], "total": i[4]},
                second={
                    "frozensell": p.frozen_sell,
                    "ava": p.avaliable_volume,
                    "total": p.market_value,
                },
            )
        gl.logger.critical("Position卖出测试完成.")

    def test_PositionUpdate(self):
        print("")
        gl.logger.critical("Position更新测试开始.")
        p = self.reset()
        p.unfreeze_t1()
        param = [
            # 0volume, 1price, 2datetime, 3ava, 4totalvolume
            (10000, 11, "2020-01-02", 10000, 20000),
            (1000, 11, "2020-01-02", 9000, 19000),
        ]
        for i in param:
            if i[0] < 0:
                p.freeze_sell(abs(i[0]))
                p.update(volume=i[0], price=i[1], datetime=i[2])
                self.assertEqual(
                    first={"ava": i[3], "volume": i[4], "date": i[2]},
                    second={
                        "ava": p.avaliable_volume,
                        "volume": p.volume,
                        "date": p.datetime.strftime("%Y-%m-%d"),
                    },
                )
        gl.logger.critical("Position更新测试完成.")

    def test_PositionMarketValue(self):
        print("")
        gl.logger.critical("Posiiton 市场价值测试开始")
        # TODO
        gl.logger.critical("Posiiton 市场价值测试结束")
