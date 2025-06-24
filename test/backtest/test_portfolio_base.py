import unittest
import uuid
from ginkgo.libs import GLOG
from ginkgo.libs.data.normalize import datetime_normalize
from ginkgo.backtest.order import Order
from ginkgo.backtest.strategies import StrategyBase
from ginkgo.libs.ginkgo_math import cal_fee
from ginkgo.enums import DIRECTION_TYPES, FREQUENCY_TYPES
from ginkgo.backtest.engines import BaseEngine, EventEngine
from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
from ginkgo.backtest.portfolios import PortfolioT1Backtest
from ginkgo.backtest.position import Position
from ginkgo.backtest.events import EventPriceUpdate, EventSignalGeneration
from ginkgo.backtest.signal import Signal
from ginkgo.libs.ginkgo_math import cal_fee
from ginkgo.backtest.selectors import FixedSelector
from ginkgo.backtest.analyzers import BaseAnalyzer
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.sizers import BaseSizer, FixedSizer
from ginkgo.backtest.risk_managements import BaseRiskManagement
from ginkgo.backtest.feeders.base_feeder import BaseFeeder


class PortfolioBaseTest(unittest.TestCase):
    """
    UnitTest for Signal.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(PortfolioBaseTest, self).__init__(*args, **kwargs)
        self.params = [
            {},
        ]

    def test_portfolio_init(self) -> None:
        p = BasePortfolio()

    def test_portfolio_addstrategy(self) -> None:
        p = BasePortfolio()
        s = StrategyBase()
        p.add_strategy(s)
        self.assertEqual(1, len(p.strategies))
        s2 = StrategyBase()
        p.add_strategy(s2)
        self.assertEqual(2, len(p.strategies))

    def test_portfolio_addposition(self) -> None:
        p = BasePortfolio()
        pos1 = Position(
            portfolio_id=p.uuid,
            engine_id=p.engine_id,
            code="test_code",
            cost=10,
            volume=1000,
            frozen_volume=0,
            frozen_money=0,
            price=10,
            fee=0,
        )
        p.add_position(pos1)
        r = p.positions["test_code"]
        self.assertEqual("test_code", r.code)
        self.assertEqual(10, r.price)
        self.assertEqual(10, r.cost)
        self.assertEqual(1000, r.volume)
        pos2 = Position(
            portfolio_id=p.uuid,
            engine_id=p.engine_id,
            code="test_code2",
            cost=10,
            volume=1000,
            frozen_volume=0,
            frozen_money=0,
            price=10,
            fee=0,
        )
        p.add_position(pos2)
        self.assertEqual(2, len(p.positions))
