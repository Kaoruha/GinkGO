import unittest
from src.backtest.broker.base_broker import BaseBroker
from src.backtest.event_engine import EventEngine
from src.backtest.strategy.base_strategy import BaseStrategy
from src.backtest.sizer.base_sizer import BaseSizer
from src.backtest.risk.base_risk import BaseRisk
from src.backtest.matcher.base_matcher import BaseMatcher
from src.backtest.analyzer.base_analyzer import BaseAnalyzer
from src.backtest.painter.base_painter import BasePainter
from src.backtest.postion import Position
from src.backtest.price_old import DayBar


class BrokerTest(unittest.TestCase):
    """
    经纪人类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(BrokerTest, self).__init__(*args, **kwargs)
        self.broker_name = 'base'
        self.engine = EventEngine()
        self.init_capital = 100000

    def reset_broker(self) -> BaseBroker:
        self.base_broker = BaseBroker(name=self.broker_name, engine=self.engine, init_capital=self.init_capital)
        return self.base_broker

    # def test_Init_OK(self) -> None:
    #     """
    #     初始化基础经纪人
    #     """
    #     test_tuple = [
    #         ('broker1', 1000), ('broker2', 0), ('broker3', 10000)
    #     ]
    #     for i in test_tuple:
    #         b = BaseBroker(name=i[0], engine=EventEngine(), init_capital=i[1])
    #         self.assertEqual(
    #             first={
    #                 "name": i[0],
    #                 "init_capital": i[1],
    #             },
    #             second={
    #                 "name": b.name,
    #                 "init_capital": b.init_capital,
    #             }
    #         )

    # def test_RegisterStrategy_FAILED(self) -> None:
    #     """
    #     注册一个非策略实例
    #     """
    #     tuple1 = [None, 'a', 1, EventEngine(), BaseRisk(), BaseMatcher(), BaseSizer(),
    #               BaseAnalyzer(), BasePainter()]
    #     b = self.reset_broker()
    #     for i in tuple1:
    #         b.strategy_register(i)
    #         self.assertEqual(
    #             first={
    #                 'length': 0
    #             },
    #             second={
    #                 'length': len(b.strategies)
    #             }
    #         )

    # def test_RegisterStrategy_OK(self) -> None:
    #     """
    #     注册策略
    #     """
    #     s = BaseStrategy(name='bb')
    #     tuple1 = [
    #         (BaseStrategy(name='s1'), 1),
    #         ('strategy', 0),
    #         (BaseStrategy(name='s2'), 1),
    #         (110, 0),
    #         (BaseStrategy(name='s2'), 1),
    #         (s, 1),
    #         (BaseSizer(), 0),
    #         (s, 0),
    #         (BaseStrategy(name='s5'), 1),
    #         (None, 0),
    #     ]
    #     b = self.reset_broker()
    #     count = 0
    #     for i in tuple1:
    #         b.strategy_register(i[0])
    #         count += i[1]
    #         self.assertEqual(
    #             first={
    #                 'length': count
    #             },
    #             second={
    #                 'length': len(b.strategies)
    #             }
    #         )

    # def test_RegisterSizer_FAILED(self) -> None:
    #     """
    #     仓位控制失败
    #     """
    #     b = self.reset_broker()
    #     tuple1 = [1, 'Sizer', BaseRisk()]
    #     for i in tuple1:
    #         b.sizer_register(i)
    #         self.assertEqual(
    #             first={
    #                 'sizer': None
    #             },
    #             second={
    #                 'sizer': b.sizer
    #             }
    #         )

    # def test_RegisterSizer_OK(self) -> None:
    #     """
    #     注册仓位控制
    #     """
    #     b = self.reset_broker()
    #     tuple1 = ['sizer1', 'none', 'None', '111', 'name11', '11name']
    #     for i in tuple1:
    #         s = BaseSizer(name=i)
    #         b.sizer_register(s)
    #         self.assertEqual(
    #             first={
    #                 'name': i
    #             },
    #             second={
    #                 'name': b.sizer.name
    #             }
    #         )
    #     tuple2 = [
    #         (BaseSizer(name='sizer11'), None, 'sizer11'),
    #         (None, BaseSizer(name='sizer111'), 'sizer111'),
    #         (BaseSizer(name='sizer22'), 'hello', 'sizer22'),
    #         ('hello', BaseSizer(name='sizer222'), 'sizer222'),
    #         (BaseSizer(name='sizer33'), BaseRisk(), 'sizer33'),
    #         (BaseRisk(), BaseSizer(name='sizer333'), 'sizer333'),
    #     ]
    #     b = self.reset_broker()
    #     for i in tuple2:
    #         b.sizer_register(i[0])
    #         b.sizer_register(i[1])
    #         self.assertEqual(
    #             first={
    #                 'name': i[2]
    #             },
    #             second={
    #                 'name': b.sizer.name
    #             }
    #         )

    # def test_RegisterRisk_FAILED(self) -> None:
    #     """
    #     注册一个非风控实例
    #     """
    #     tuple1 = [None, 'a', 1, EventEngine(), BaseStrategy(), BaseMatcher(), BaseSizer(),
    #               BaseAnalyzer(), BasePainter()]
    #     b = self.reset_broker()
    #     for i in tuple1:
    #         b.risk_register(i)
    #         self.assertEqual(
    #             first={
    #                 'length': 0
    #             },
    #             second={
    #                 'length': len(b.risk_management)
    #             }
    #         )

    # def test_RegisterRisk_OK(self) -> None:
    #     """
    #     注册风控实例
    #     """
    #     s = BaseRisk(name='bb')
    #     tuple1 = [
    #         (BaseRisk(name='s1'), 1),
    #         ('strategy', 0),
    #         (BaseRisk(name='s2'), 1),
    #         (110, 0),
    #         (BaseRisk(name='s2'), 1),
    #         (s, 1),
    #         (BaseSizer(), 0),
    #         (s, 0),
    #         (BaseRisk(name='s5'), 1),
    #         (None, 0),
    #     ]
    #     b = self.reset_broker()
    #     count = 0
    #     for i in tuple1:
    #         b.risk_register(i[0])
    #         count += i[1]
    #         self.assertEqual(
    #             first={
    #                 'length': count
    #             },
    #             second={
    #                 'length': len(b.risk_management)
    #             }
    #         )

    # def test_RegisterMatcher_FAILED(self) -> None:
    #     """
    #     撮合单元注册失败
    #     """
    #     b = self.reset_broker()
    #     tuple1 = [1, 'Matcher', BaseRisk()]
    #     for i in tuple1:
    #         b.matcher_register(i)
    #         self.assertEqual(
    #             first={
    #                 'matcher': None
    #             },
    #             second={
    #                 'matcher': b.matcher
    #             }
    #         )

    # def test_RegisterMatcher_OK(self) -> None:
    #     """
    #     撮合单元注册成功
    #     """
    #     b = self.reset_broker()
    #     tuple1 = ['matcher', 'none', 'None', '111', 'name11', '11name']
    #     for i in tuple1:
    #         m = BaseMatcher(name=i)
    #         b.matcher_register(m)
    #         self.assertEqual(
    #             first={
    #                 'name': i
    #             },
    #             second={
    #                 'name': b.matcher.name
    #             }
    #         )
    #     tuple2 = [
    #         (BaseMatcher(name='matcher11'), None, 'matcher11'),
    #         (None, BaseMatcher(name='matcher111'), 'matcher111'),
    #         (BaseMatcher(name='matcher22'), 'hello', 'matcher22'),
    #         ('hello', BaseMatcher(name='matcher222'), 'matcher222'),
    #         (BaseMatcher(name='matcher33'), BaseRisk(), 'matcher33'),
    #         (BaseRisk(), BaseMatcher(name='matcher333'), 'matcher333'),
    #     ]
    #     b = self.reset_broker()
    #     for i in tuple2:
    #         b.matcher_register(i[0])
    #         b.matcher_register(i[1])
    #         self.assertEqual(
    #             first={
    #                 'name': i[2]
    #             },
    #             second={
    #                 'name': b.matcher.name
    #             }
    #         )

    # def test_RegisterAnalyzer_FAILED(self) -> None:
    #     """
    #     分析单元注册失败
    #     """
    #     b = self.reset_broker()
    #     tuple1 = [1, 'Analyzer', BaseSizer()]
    #     for i in tuple1:
    #         b.analyzer_register(i)
    #         self.assertEqual(
    #             first={
    #                 'analyzer': None
    #             },
    #             second={
    #                 'analyzer': b.analyzer
    #             }
    #         )

    # def test_RegisterAnalyzer_OK(self) -> None:
    #     """
    #     分析单元注册成功
    #     """
    #     b = self.reset_broker()
    #     tuple1 = ['matcher', 'none', 'None', '111', 'name11', '11name']
    #     for i in tuple1:
    #         a = BaseAnalyzer(name=i)
    #         b.analyzer_register(a)
    #         self.assertEqual(
    #             first={
    #                 'name': i
    #             },
    #             second={
    #                 'name': b.analyzer.name
    #             }
    #         )
    #     tuple2 = [
    #         (BaseAnalyzer(name='analyzer11'), None, 'analyzer11'),
    #         (None, BaseAnalyzer(name='analyzer111'), 'analyzer111'),
    #         (BaseAnalyzer(name='analyzer22'), 'hello', 'analyzer22'),
    #         ('hello', BaseAnalyzer(name='analyzer222'), 'analyzer222'),
    #         (BaseAnalyzer(name='analyzer33'), BaseRisk(), 'analyzer33'),
    #         (BaseRisk(), BaseAnalyzer(name='analyzer333'), 'analyzer333'),
    #     ]
    #     b = self.reset_broker()
    #     for i in tuple2:
    #         b.analyzer_register(i[0])
    #         b.analyzer_register(i[1])
    #         self.assertEqual(
    #             first={
    #                 'name': i[2]
    #             },
    #             second={
    #                 'name': b.analyzer.name
    #             }
    #         )

    # def test_RegisterPainter_FAILED(self) -> None:
    #     """
    #     绘图单元注册失败
    #     """
    #     b = self.reset_broker()
    #     tuple1 = [1, 'Painter', BaseSizer()]
    #     for i in tuple1:
    #         b.painter_register(i)
    #         self.assertEqual(
    #             first={
    #                 'painter': None
    #             },
    #             second={
    #                 'painter': b.painter
    #             }
    #         )

    # def test_RegisterPainter_OK(self) -> None:
    #     """
    #     绘图单元注册成功
    #     """
    #     b = self.reset_broker()
    #     tuple1 = ['painter', 'none', 'None', '111', 'name11', '11name']
    #     for i in tuple1:
    #         p = BasePainter(name=i)
    #         b.painter_register(p)
    #         self.assertEqual(
    #             first={
    #                 'name': i
    #             },
    #             second={
    #                 'name': b.painter.name
    #             }
    #         )
    #     tuple2 = [
    #         (BasePainter(name='painter11'), None, 'painter11'),
    #         (None, BasePainter(name='painter111'), 'painter111'),
    #         (BasePainter(name='painter22'), 'hello', 'painter22'),
    #         ('hello', BasePainter(name='painter222'), 'painter222'),
    #         (BasePainter(name='painter33'), BaseRisk(), 'painter33'),
    #         (BaseRisk(), BasePainter(name='painter333'), 'painter333'),
    #     ]
    #     b = self.reset_broker()
    #     for i in tuple2:
    #         b.painter_register(i[0])
    #         b.painter_register(i[1])
    #         self.assertEqual(
    #             first={
    #                 'name': i[2]
    #             },
    #             second={
    #                 'name': b.painter.name
    #             }
    #         )

    # def test_GetCash_FAILED(self) -> None:
    #     """
    #     经纪人入金失败
    #     """
    #     tuple1 = [('money', 100000), (-200, 100000)]
    #     for i in tuple1:
    #         b = self.reset_broker()
    #         b.get_cash((i[0]))
    #         self.assertEqual(
    #             first={
    #                 'capital': i[1]
    #             },
    #             second={
    #                 'capital': b.capital
    #             }
    #         )

    # def test_GetCash_OK(self) -> None:
    #     """
    #     经纪人实例入金成功
    #     """
    #     # 入金1次
    #     tuple1 = [(10000, 110000), (0, 100000)]
    #     for i in tuple1:
    #         b = self.reset_broker()
    #         b.get_cash(i[0])
    #         self.assertEqual(
    #             first={
    #                 "init_capital": self.init_capital + i[0],
    #                 "capital": self.init_capital + i[0]
    #             },
    #             second={
    #                 "init_capital": i[1],
    #                 "capital": i[1]
    #             }
    #         )

    #     # 入金2次
    #     tuple2 = [
    #         (10000, 20000, 130000),
    #         (10000, 0, 110000),
    #         (0, 10000, 110000),
    #         ('money', 10000, 110000),
    #         (10000, 'money', 110000),
    #         (-10000, 10000, 110000),
    #         (10000, -20000, 110000),
    #         (10000.111, -20000.111, 110000.111)
    #     ]
    #     for i in tuple2:
    #         b = self.reset_broker()
    #         b.get_cash(i[0])
    #         b.get_cash(i[1])
    #         self.assertEqual(
    #             first={
    #                 'capital': i[2]
    #             },
    #             second={
    #                 'capital': b.capital
    #             }
    #         )

    # def test_FreezeMoney_FAILED(self) -> None:
    #     """
    #     冻结现金失败
    #     """
    #     tuple1 = ['1000 dollar', '-20000', '-4000.0', '0', '0.0', '$1000', '10000$', '100000000']
    #     b = self.reset_broker()
    #     for i in tuple1:
    #         b.freeze_money(i)
    #         self.assertEqual(
    #             first={
    #                 'freeze': 0,
    #                 'capital': self.init_capital
    #             },
    #             second={
    #                 'freeze': b.freeze,
    #                 'capital': b.capital
    #             }
    #         )

    # def test_FreezeMoney_OK(self) -> None:
    #     """
    #     冻结现金成功
    #     """
    #     tuple1 = [
    #         (10000, 90000, 10000),
    #         (10000, 80000, 20000),
    #         (0, 80000, 20000),
    #         (-10000, 80000, 20000),
    #         (100000, 80000, 20000),
    #         (50000, 30000, 70000)
    #     ]
    #     b = self.reset_broker()
    #     capital = self.init_capital
    #     for i in tuple1:
    #         b.freeze_money(i[0])
    #         self.assertEqual(
    #             first={
    #                 'freeze': i[2],
    #                 'capital': i[1]
    #             },
    #             second={
    #                 'freeze': b.freeze,
    #                 'capital': b.capital
    #             }
    #         )

    # def test_AddPosition_OK(self) -> None:
    #     """
    #     增加持仓成功
    #     """
    #     b = self.reset_broker()
    #     tuple1 = [
    #         ('test1', 10, 1000, '2020-01-01', 1, 10000),
    #         ('test1', 11, 1000, '2020-01-02', 1, 22000),
    #         ('test2', 20, 2000, '2020-01-02', 2, 62000),
    #         ('test2', 10, 2000, '2020-01-02', 2, 62000),
    #     ]
    #     for i in tuple1:
    #         r = b.add_position(Position(code=i[0], cost=i[1], volume=i[2], date=i[3]))
    #         self.assertEqual(
    #             first={
    #                 'count': i[4],
    #                 'total': i[5]
    #             },
    #             second={
    #                 'count': len(r),
    #                 'total': b.cal_position()
    #             }
    #         )

    # def test_FreezePosition_OK(self) -> None:
    #     """
    #     冻结持仓
    #     """
    #     b = self.reset_broker()
    #     b.add_position(Position(code='t1', cost=10, volume=5000, date='2020-01-01'))
    #     b.add_position(Position(code='t2', cost=20, volume=1000, date='2020-01-01'))
    #     tuple1 = [
    #         ('t1', 500, '2020-01-01', 500, 4500),
    #         ('t2', 500, '2020-01-01', 500, 500),
    #         ('t1', 500, '2020-01-01', 1000, 4000),
    #         ('t2', 500, '2020-01-01', 1000, 0),
    #     ]
    #     for i in tuple1:
    #         b.freeze_position(code=i[0], volume=i[1], date=i[2])
    #         self.assertEqual(
    #             first={
    #                 'frozen': i[3],
    #                 'hold': i[4]
    #             },
    #             second={
    #                 'frozen': b.position[i[0]].freeze,
    #                 'hold': b.position[i[0]].volume
    #             }
    #         )

    # def test_RestorePosition_OK(self) -> None:
    #     """
    #     恢复冻结的持仓
    #     """
    #     b = self.reset_broker()
    #     b.add_position(Position(code='t1', cost=10, volume=5000, date='2020-01-01'))
    #     b.add_position(Position(code='t2', cost=20, volume=1000, date='2020-01-01'))
    #     b.freeze_position('t1', volume=3000, date='2020-01-02')
    #     b.freeze_position('t2', volume=500, date='2020-01-02')
    #     tuple1 = [
    #         ('t1', 500, '2020-01-01', 2500, 2500),
    #         ('t2', 500, '2020-01-01', 0, 1000),
    #         ('t2', 500, '2020-01-01', 0, 1000),
    #         ('t1', 500, '2020-01-01', 2000, 3000),
    #     ]
    #     for i in tuple1:
    #         b.restore_frozen_position(code=i[0], volume=i[1], date=i[2])
    #         self.assertEqual(
    #             first={
    #                 'frozen': i[3],
    #                 'hold': i[4]
    #             },
    #             second={
    #                 'frozen': b.position[i[0]].freeze,
    #                 'hold': b.position[i[0]].volume
    #             }
    #         )

    # def test_ReducePosition_OK(self) -> None:
    #     """
    #     成功卖出
    #     """
    #     b = self.reset_broker()
    #     b.add_position(Position(code='t1', cost=10, volume=5000, date='2020-01-01'))
    #     b.add_position(Position(code='t2', cost=20, volume=1000, date='2020-01-01'))
    #     b.freeze_position('t1', volume=3000, date='2020-01-02')
    #     b.freeze_position('t2', volume=500, date='2020-01-02')
    #     tuple1 = [
    #         ('t1', 500, '2020-01-01', 2500, 2000),
    #         ('t2', 500, '2020-01-01', 0, 500),
    #         ('t2', 500, '2020-01-01', 0, 500),
    #         ('t1', 500, '2020-01-01', 2000, 2000),
    #     ]
    #     for i in tuple1:
    #         b.reduce_position(code=i[0], volume=i[1], date=i[2])
    #         self.assertEqual(
    #             first={
    #                 'frozen': i[3],
    #                 'hold': i[4]
    #             },
    #             second={
    #                 'frozen': b.position[i[0]].freeze,
    #                 'hold': b.position[i[0]].volume
    #             }
    #         )

    # def test_CalPosition_OK(self) -> None:
    #     """
    #     计算持仓总价值
    #     """
    #     b = self.reset_broker()
    #     tuple1 = [
    #         ('t1', 10, 1000, '2020-01-01', 10000),
    #         ('t1', 10, 1000, '2020-01-02', 20000),
    #         ('t2', 10, 1000, '2020-01-02', 30000),
    #         ('t3', 10, 1000, '2020-01-02', 40000),
    #         ('t3', 20, 1000, '2020-01-02', 70000),
    #     ]
    #     for i in tuple1:
    #         b.add_position(Position(code=i[0], cost=i[1], volume=i[2], date=i[3]))
    #         self.assertEqual(
    #             first={
    #                 'total': i[4]
    #             },
    #             second={
    #                 'total': b.cal_position()
    #             }
    #         )
    #     tuple2 = [
    #         ('t1', 2000, '2020-01-01', 70000),
    #         ('t2', 500, '2020-01-01', 70000),
    #         ('t3', 500, '2020-01-01', 70000),
    #     ]
    #     for i in tuple2:
    #         b.freeze_position(code=i[0], volume=i[1], date=i[2])
    #         self.assertEqual(
    #             first={
    #                 'total': i[3]
    #             },
    #             second={
    #                 'total': b.cal_position()
    #             }
    #         )

    #     tuple3 = [
    #         ('t1', 2000, '2020-01-01', 50000),
    #         ('t2', 500, '2020-01-01', 45000),
    #     ]
    #     for i in tuple3:
    #         b.reduce_position(code=i[0], volume=i[1], date=i[2])
    #         self.assertEqual(
    #             first={
    #                 'total': i[3]
    #             },
    #             second={
    #                 'total': b.cal_position()
    #             }
    #         )

    # def test_CleanPosition_OK(self) -> None:
    #     """
    #     清理持仓
    #     """
    #     b = self.reset_broker()
    #     b.add_position(Position(code='t1', cost=10, volume=5000, date='2020-01-01'))
    #     b.add_position(Position(code='t2', cost=20, volume=1000, date='2020-01-01'))
    #     b.freeze_position('t1', volume=5000, date='2020-01-02')
    #     b.freeze_position('t2', volume=1000, date='2020-01-02')
    #     tuple1 = [
    #         ('t1', 2000, '2020-01-03', 2),
    #         ('t1', 2000, '2020-01-03', 2),
    #         ('t1', 2000, '2020-01-03', 2),
    #         ('t1', 1000, '2020-01-03', 1),
    #         ('t2', 1000, '2020-01-03', 0),
    #     ]
    #     for i in tuple1:
    #         b.reduce_position(code=i[0], volume=i[1], date=i[2])
    #         self.assertEqual(
    #             first={
    #                 'len': i[3]
    #             },
    #             second={
    #                 'len': len(b.position)
    #             }
    #         )

    # def test_UpdateDate_FAILED(self) -> None:
    #     """
    #     日期更新失败
    #     """
    #     # TODO
    #     pass

    # def test_UpdateDate_OK(self) -> None:
    #     """
    #     日期更新成功
    #     """
    #     # TODO
    #     pass

    # def test_UpdateTime_FAILED(self) -> None:
    #     """
    #     时间更新失败
    #     """
    #     # TODO
    #     pass

    # def test_UpdateTime_OK(self) -> None:
    #     """
    #     时间更新成功
    #     """
    #     # TODO
    #     pass

    # def test_UpdatePrice_FAILED(self) -> None:
    #     """
    #     价格更新失败
    #     """
    #     pass

    # def test_UpdatePrice_OK(self) -> None:
    #     """
    #     价格更新成功
    #     """
    #     b = self.reset_broker()
    #     b.add_position(Position(code='t1', cost=10, volume=5000, date='2020-01-01'))
    #     b.add_position(Position(code='t2', cost=20, volume=1000, date='2020-01-01'))
    #     tuple1 = [
    #         ('t1', 1, '2020-02-02', 25000),
    #         ('t1', 2, '2020-02-02', 30000),
    #         ('t2', 1, '2020-02-02', 11000),
    #         ('t3', 1, '2020-02-02', 11000),
    #         ('t2', 10, '2020-02-02', 20000),
    #     ]
    #     for i in tuple1:
    #         price = DayBar(date=i[2], code=i[0], open_=1, high=2, low=1, close=i[1], pre_close=i[1], volume=1000,
    #                        amount=10000, adjust_flag=0, turn=.1, pct_change=.1, is_st=0)
    #         b.update_price(price)
    #         self.assertEqual(
    #             first={
    #                 'total': i[3]
    #             },
    #             second={
    #                 'total': b.cal_position()
    #             }
    #         )

    # def test_CalCapital_OK(self) -> None:
    #     """
    #     计算更新总资金
    #     """
    #     b = self.reset_broker()
    #     tuple1 = [
    #         (50000, 100000),
    #         (0, 100000),
    #         (80000, 100000)
    #     ]
    #     for i in tuple1:
    #         b.freeze_money(i[0])
    #         self.assertEqual(
    #             first={
    #                 'total': i[1]
    #             },
    #             second={
    #                 'total': b.cal_total_capital()
    #             }
    #         )

    # def test_AddHistory_FAILED(self) -> None:
    #     """
    #     增加交易历史失败
    #     """
    #     # TODO
    #     pass

    # def test_AddHistory_OK(self) -> None:
    #     """
    #     增加交易历史成功
    #     """
    #     # TODO
    #     pass