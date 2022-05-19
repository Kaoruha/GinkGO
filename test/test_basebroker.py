import unittest
from ginkgo.backtest.broker.base_broker import BaseBroker
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.selector.random_selector import RandomSelector
from ginkgo.backtest.strategy.profit_loss_limit import ProfitLossLimit
from ginkgo.backtest.sizer.base_sizer import BaseSizer
from ginkgo.backtest.sizer.full_sizer import FullSizer
from ginkgo.backtest.matcher.simulate_matcher import SimulateMatcher
from ginkgo.backtest.painter.candle import CandlePainter
from ginkgo.backtest.analyzer.base_analyzer import BaseAnalyzer
from ginkgo.backtest.analyzer.benchmark import BenchMark
from ginkgo.backtest.postion import Position
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.libs import GINKGOLOGGER as gl


class BrokerTest(unittest.TestCase):
    """
    经纪人类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(BrokerTest, self).__init__(*args, **kwargs)
        self.broker_name = "testbroker"
        self.engine = EventEngine()
        self.init_capital = 100000

    def reset(self) -> BaseBroker:
        self.base_broker = BaseBroker(
            name=self.broker_name, engine=self.engine, init_capital=self.init_capital
        )
        return self.base_broker

    def test_Init_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker初始化测试开始.")
        params = [
            # 0brokername, 1init_cash
            ("broker1", 1000),
            ("broker2", 0),
            ("broker3", 10000),
        ]
        for i in params:
            b = BaseBroker(name=i[0], engine=EventEngine(), init_capital=i[1])
            gl.logger.info(b)
            self.assertEqual(
                first={
                    "name": i[0],
                    "init_capital": i[1],
                },
                second={
                    "name": b.name,
                    "init_capital": b.init_capital,
                },
            )
        gl.logger.critical("BaseBroker初始化测试完成.")

    def test_RegisterSelector_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker选股模块注册测试开始.")
        b = self.reset()
        params = [
            (),
        ]
        for i in params:
            s = RandomSelector()
            b.selector_register(s)
            self.assertNotEqual(
                first={"selector": None}, second={"selector": b.selector}
            )
        gl.logger.critical("BaseBroker选股模块注册测试完成.")

    def test_RegisterStrategy_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker策略注册测试开始.")
        s = ProfitLossLimit(name="test_strategy")
        params = [
            # 0strategy, 1strategy_count
            (ProfitLossLimit(name="s1"), 1),
            ("strategy", 0),
            (s, 1),
            (s, 0),
            (ProfitLossLimit(name="s1"), 1),
            (110, 0),
            (ProfitLossLimit(name="s2"), 1),
            (ProfitLossLimit(name="s2"), 1),
            (None, 0),
        ]
        b = self.reset()
        count = 0
        for i in params:
            b.strategy_register(i[0])
            gl.logger.info(b)
            count += i[1]
            self.assertEqual(
                first={"length": count}, second={"length": len(b.strategies)}
            )
        gl.logger.critical("BaseBroker策略注册测试完成.")

    def test_RegisterSizer_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker仓位控注册测试开始.")
        b = self.reset()
        sizer_params = ["sizer1", "none", "None", "111", "name11", "11name"]
        for i in sizer_params:
            s = FullSizer(name=i)
            b.sizer_register(s)
            self.assertEqual(first={"name": i}, second={"name": b.sizer.name})
        params = [
            # 0sizer0, 1sizer1, 2finalsizername
            (FullSizer(name="sizer11"), None, "sizer11"),
            (None, FullSizer(name="sizer111"), "sizer111"),
            (FullSizer(name="sizer22"), "hello", "sizer22"),
            ("hello", FullSizer(name="sizer222"), "sizer222"),
            (FullSizer(name="sizer33"), ProfitLossLimit(), "sizer33"),
            (FullSizer(), FullSizer(name="sizer333"), "sizer333"),
        ]
        b = self.reset()
        for i in params:
            b.sizer_register(i[0])
            b.sizer_register(i[1])
            self.assertEqual(first={"name": i[2]}, second={"name": b.sizer.name})
        gl.logger.critical("BaseBroker仓位控注册测试结束.")

        def test_RegisterRisk_OK(self) -> None:
            """
            注册风控实例
            """
            pass

    def test_RegisterMatcher_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker撮合单元注册测试开始.")
        b = self.reset()
        matcher_params = ["matcher", "none", "None", "111", "name11", "11name"]
        for i in matcher_params:
            m = SimulateMatcher(name=i)
            b.matcher_register(m)
            self.assertEqual(first={"name": i}, second={"name": b.matcher.name})
        step_params = [
            # 0matcher0,1matcher1,2finalmatchername
            (SimulateMatcher(name="matcher11"), None, "matcher11"),
            (None, SimulateMatcher(name="matcher111"), "matcher111"),
            (SimulateMatcher(name="matcher22"), "hello", "matcher22"),
            ("hello", SimulateMatcher(name="matcher222"), "matcher222"),
            (SimulateMatcher(name="matcher33"), ProfitLossLimit(), "matcher33"),
            (ProfitLossLimit(), SimulateMatcher(name="matcher333"), "matcher333"),
        ]
        b = self.reset()
        for i in step_params:
            b.matcher_register(i[0])
            b.matcher_register(i[1])
            self.assertEqual(first={"name": i[2]}, second={"name": b.matcher.name})
        gl.logger.critical("BaseBroker撮合单元注册测试结束.")

    def test_RegisterAnalyzer_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker分析器注册测试开始.")
        b = self.reset()
        params1 = ["matcher", "none", "None", "111", "name11", "11name"]
        for i in params1:
            a = BenchMark(name=i)
            b.analyzer_register(a)
            self.assertEqual(first={"name": i}, second={"name": b.analyzer.name})
        params2 = [
            # 0analyzer0,1analyzer1, 2finalanalyzername
            (BenchMark(name="analyzer11"), None, "analyzer11"),
            (None, BenchMark(name="analyzer111"), "analyzer111"),
            (BenchMark(name="analyzer22"), "hello", "analyzer22"),
            ("hello", BenchMark(name="analyzer222"), "analyzer222"),
            (BenchMark(name="analyzer33"), ProfitLossLimit(), "analyzer33"),
            (ProfitLossLimit(), BenchMark(name="analyzer333"), "analyzer333"),
        ]
        b = self.reset()
        for i in params2:
            b.analyzer_register(i[0])
            b.analyzer_register(i[1])
            self.assertEqual(first={"name": i[2]}, second={"name": b.analyzer.name})
        gl.logger.critical("BaseBroker分析器注册测试完成.")

    def test_RegisterPainter_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker绘图模块注册测试开始.")
        b = self.reset()
        params1 = ["painter", "none", "None", "111", "name11", "11name"]
        for i in params1:
            p = CandlePainter(name=i)
            b.painter_register(p)
            self.assertEqual(first={"name": i}, second={"name": b.painter.name})
        params2 = [
            # 0painter0,1painter1,2finalpaintername
            (CandlePainter(name="painter11"), None, "painter11"),
            (None, CandlePainter(name="painter111"), "painter111"),
            (CandlePainter(name="painter22"), "hello", "painter22"),
            ("hello", CandlePainter(name="painter222"), "painter222"),
            (CandlePainter(name="painter33"), ProfitLossLimit(), "painter33"),
            (ProfitLossLimit(), CandlePainter(name="painter333"), "painter333"),
        ]
        b = self.reset()
        for i in params2:
            b.painter_register(i[0])
            b.painter_register(i[1])
            self.assertEqual(first={"name": i[2]}, second={"name": b.painter.name})
        gl.logger.critical("BaseBroker绘图模块注册测试完成.")

    def test_GetCash_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker入金测试开始.")
        # 入金1次
        params1 = [
            # 0getcash,1 capital
            (10000, 110000),
            (0, 100000),
        ]
        for i in params1:
            b = self.reset()
            b.get_cash(i[0])
            self.assertEqual(
                first={
                    "init_capital": self.init_capital + i[0],
                    "capital": self.init_capital + i[0],
                },
                second={"init_capital": i[1], "capital": i[1]},
            )

        params2 = [
            # 0 get0,1 get1,2capital
            (10000, 20000, 130000),
            (10000, 0, 110000),
            (0, 10000, 110000),
            ("money", 10000, 110000),
            (10000, "money", 110000),
            (-10000, 10000, 110000),
            (10000, -20000, 110000),
            (10000.111, -20000.111, 110000.111),
        ]
        for i in params2:
            b = self.reset()
            b.get_cash(i[0])
            b.get_cash(i[1])
            self.assertEqual(first={"capital": i[2]}, second={"capital": b.capital})
        gl.logger.critical("BaseBroker入金测试完成.")

    def test_FreezeMoney_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker冻结现金测试开始.")
        params1 = [
            # 0freezemoney,1capital,2frozenmoney
            (10000, 90000, 10000),
            (10000, 80000, 20000),
            (0, 80000, 20000),
            (-10000, 80000, 20000),
            (100000, 80000, 20000),
            (50000, 30000, 70000),
        ]
        b = self.reset()
        capital = self.init_capital
        for i in params1:
            b.freeze_money(i[0])
            self.assertEqual(
                first={"freeze": i[2], "capital": i[1]},
                second={"freeze": b.frozen_capital, "capital": b.capital},
            )
        gl.logger.critical("BaseBroker冻结现金测试完成.")

        # def test_GetNewPrice_OK(self) -> None:
        #     pass

    def test_AddPosition_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker增加持仓测试开始.")
        b = self.reset()
        params = [
            # 0code, 1price, 2volume,3date 4,count,5total_value
            ("test1", 10, 1000, "2020-01-01", 1, 10000),
            ("test1", 11, 1000, "2020-01-02", 1, 22000),
            ("test2", 20, 2000, "2020-01-02", 2, 62000),
            ("test2", 10, 2000, "2020-01-02", 2, 62000),
        ]
        for i in params:
            r = b.add_position(code=i[0], price=i[1], volume=i[2], datetime=i[3])
            self.assertEqual(
                first={"count": i[4], "total": float(i[5])},
                second={"count": len(r), "total": b.position_value},
            )
        gl.logger.critical("BaseBroker增加持仓测试完成.")

    def test_FreezePosition_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker冻结仓位测试开始")
        b = self.reset()
        b.add_position(code="t1", price=10, volume=5000, datetime="2020-01-01")
        b.add_position(code="t2", price=20, volume=1000, datetime="2020-01-01")
        for i, v in b.position.items():
            v.unfreeze_t1()
        params = [
            # 0code,1volume,2datetime,3frozen_sell,4aviliable_volume
            ("t1", 500, "2020-01-01", 500, 4500),
            ("t2", 500, "2020-01-01", 500, 500),
            ("t1", 500, "2020-01-01", 1000, 4000),
            ("t2", 500, "2020-01-01", 1000, 0),
        ]

        for i in params:
            b.freeze_position(code=i[0], volume=i[1], datetime=i[2])
            self.assertEqual(
                first={"frozen": i[3], "hold": i[4]},
                second={
                    "frozen": b.position[i[0]].frozen_sell,
                    "hold": b.position[i[0]].avaliable_volume,
                },
            )
        gl.logger.critical("BaseBroker冻结仓位测试结束")

    def test_RestorePosition_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker持仓头寸恢复冻结测试开始.")
        b = self.reset()
        b.add_position(code="t1", price=10, volume=5000, datetime="2020-01-01")
        b.add_position(code="t2", price=20, volume=1000, datetime="2020-01-01")
        for i, v in b.position.items():
            v.unfreeze_t1()
        b.position["t1"].freeze_position(volume=5000, datetime="2020-01-01")
        b.position["t2"].freeze_position(volume=1000, datetime="2020-01-01")
        params = [
            # 0code,1freezevolume,2datetime,3frozen,4hold
            ("t1", 500, "2020-01-01", 4500, 5000),
            ("t2", 500, "2020-01-01", 500, 1000),
            ("t2", 0, "2020-01-01", 500, 1000),
            ("t2", 500, "2020-01-01", 0, 1000),
            ("t1", 500, "2020-01-01", 4000, 5000),
        ]
        for i in params:
            b.restore_frozen_position(code=i[0], volume=i[1], datetime=i[2])
            self.assertEqual(
                first={"frozen": i[3], "hold": i[4]},
                second={
                    "frozen": b.position[i[0]].frozen_sell,
                    "hold": b.position[i[0]].volume,
                },
            )
        gl.logger.critical("BaseBroker持仓头寸恢复冻结测试完成.")

    def test_ReducePosition_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker头寸减持卖出测试开始.")
        b = self.reset()
        b.add_position(code="t1", price=10, volume=5000, datetime="2020-01-01")
        b.add_position(code="t2", price=20, volume=1000, datetime="2020-01-01")
        for i, v in b.position.items():
            v.unfreeze_t1()
        b.freeze_position("t1", volume=3000, datetime="2020-01-02")
        b.freeze_position("t2", volume=500, datetime="2020-01-02")
        params = [
            ("t1", 500, "2020-01-01", 2500, 4500),
            ("t2", 1000, "2020-01-01", 500, 1000),
            ("t2", 500, "2020-01-01", 0, 500),
            ("t2", 500, "2020-01-01", 0, 500),
            ("t1", 500, "2020-01-01", 2000, 4000),
        ]
        for i in params:
            b.reduce_position(code=i[0], volume=i[1], datetime=i[2])
            self.assertEqual(
                first={"frozen": i[3], "hold": i[4]},
                second={
                    "frozen": b.position[i[0]].frozen_sell,
                    "hold": b.position[i[0]].volume,
                },
            )
        gl.logger.critical("BaseBroker头寸减持卖出测试完成.")

    def test_CalPosition_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker持仓计算测试完成.")
        b = self.reset()
        add_params = [
            # 0code,1price,2volume,3date,4value
            ("t1", 10, 1000, "2020-01-01", 10000),
            ("t1", 10, 1000, "2020-01-02", 20000),
            ("t2", 10, 1000, "2020-01-02", 30000),
            ("t3", 10, 1000, "2020-01-02", 40000),
            ("t3", 20, 1000, "2020-01-02", 70000),
        ]
        for i in add_params:
            b.add_position(code=i[0], price=i[1], volume=i[2], datetime=i[3])
            self.assertEqual(first={"total": i[4]}, second={"total": b.position_value})

        for i, v in b.position.items():
            v.unfreeze_t1()

        self.assertEqual(
            first={"total": add_params[-1][4]}, second={"total": b.position_value}
        )

        freeze_params = [
            # 0code,1freezevolume,2date,3value
            ("t1", 2000, "2020-01-01", 70000),
            ("t2", 500, "2020-01-01", 70000),
            ("t3", 500, "2020-01-01", 70000),
        ]
        for i in freeze_params:
            b.freeze_position(code=i[0], volume=i[1], datetime=i[2])
            self.assertEqual(first={"total": i[3]}, second={"total": b.position_value})

        reduce_params = [
            ("t1", 2000, "2020-01-01", 50000),
            ("t2", 500, "2020-01-01", 45000),
            ("t3", 100, "2020-01-01", 43000),
        ]
        for i in reduce_params:
            b.reduce_position(code=i[0], volume=i[1], datetime=i[2])
            self.assertEqual(first={"total": i[3]}, second={"total": b.position_value})
        gl.logger.critical("BaseBroker持仓计算测试完成.")

    def test_CleanPosition_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker持仓清理测试开始")
        b = self.reset()
        b.add_position(code="t1", price=10, volume=5000, datetime="2020-01-01")
        b.add_position(code="t2", price=20, volume=1000, datetime="2020-01-01")
        for i, v in b.position.items():
            v.unfreeze_t1()
        b.freeze_position(code="t1", volume=5000, datetime="2020-01-02")
        b.freeze_position(code="t2", volume=1000, datetime="2020-01-02")
        params = [
            ("t1", 2000, "2020-01-03", 2),
            ("t1", 2000, "2020-01-03", 2),
            ("t1", 2000, "2020-01-03", 2),
            ("t1", 1000, "2020-01-03", 1),
            ("t2", 1000, "2020-01-03", 0),
        ]
        for i in params:
            b.reduce_position(code=i[0], volume=i[1], datetime=i[2])
            self.assertEqual(first={"len": i[3]}, second={"len": len(b.position)})
        gl.logger.critical("BaseBroker持仓清理测试结束")

    def test_UpdateDate_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker日期更新测试开始")
        pass
        gl.logger.critical("BaseBroker日期更新测试结束")

    def test_UpdatePrice_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker价格更新测试开始")
        b = self.reset()
        b.add_position(code="t1", price=10, volume=5000, datetime="2020-01-01")
        b.add_position(code="t2", price=20, volume=1000, datetime="2020-01-01")
        params = [
            # 0code,1price,2date,3value
            ("t1", 1, "2020-02-02", 25000),
            ("t1", 2, "2020-02-02", 30000),
            ("t2", 1, "2020-02-02", 11000),
            ("t3", 1, "2020-02-02", 11000),
            ("t2", 10, "2020-02-02", 20000),
        ]
        for i in params:
            b.update_price(code=i[0], datetime=i[2], price=i[1])
            self.assertEqual(first={"total": i[3]}, second={"total": b.position_value})
        gl.logger.critical("BaseBroker价格更新测试结束")

    def test_CalCapital_OK(self) -> None:
        print("")
        gl.logger.critical("BaseBroker资产计算测试开始")
        b = self.reset()
        params = [(50000, 100000), (0, 100000), (80000, 100000)]
        for i in params:
            b.freeze_money(i[0])

            self.assertEqual(first={"total": i[1]}, second={"total": b.total_capital})
        pos_params = [
            # 0code, 1price, 2volume,3date 4,count,5total_value
            ("test1", 10, 1000, "2020-01-01", 1, 10000),
            ("test1", 11, 1000, "2020-01-02", 1, 22000),
            ("test2", 20, 2000, "2020-01-02", 2, 62000),
            ("test2", 10, 2000, "2020-01-02", 2, 62000),
        ]
        for i in pos_params:
            r = b.add_position(code=i[0], price=i[1], volume=i[2], datetime=i[3])
            self.assertEqual(
                first={"total": params[-1][1] + i[5]}, second={"total": b.total_capital}
            )

        gl.logger.critical("BaseBroker资产计算测试结束")

    def test_Next_OK(self):
        print("")
        gl.logger.critical("BaseBroker下一天测试开始")
        b = self.reset()
        while True:
            if not b.next():
                break
        gl.logger.critical("BaseBroker下一天测试完成")

    # def test_AddHistory_OK(self) -> None:
    #     """
    #     增加交易历史成功
    #     """
    #     # TODO
    #     pass