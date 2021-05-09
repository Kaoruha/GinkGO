from ginkgo.backtest.sizer.risk_avg_sizer import RiskAVGSizer
from ginkgo.backtest.events import (
    SignalEvent,
    DealType,
    EventType,
    MarketEvent,
    InfoType,
)
from ginkgo.backtest.broker.T_1_broker import T1Broker
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.postion import Position
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.backtest.matcher.simulate_matcher import SimulateMatcher
from ginkgo.backtest.strategy.test_strategy import TestStrategy
from ginkgo.backtest.strategy.trend_follow import TrendFollow
from ginkgo.backtest.price import DayBar
from ginkgo.util.stock_filter import remove_index
from ginkgo.backtest.painter.candle import CandlePainter

r = RiskAVGSizer(base_factor=8000)

engine = EventEngine()
broker = T1Broker(init_capitial=100000, engine=engine)
engine.register(EventType.Market, broker.market_handler)
engine.register(EventType.Signal, broker.signal_handler)
engine.register(EventType.Order, broker.order_handler)
engine.register(EventType.Fill, broker.fill_handler)
# tf_strategy = TestStrategy()
short_ = 5
long_ = 20
tf_strategy = TrendFollow(short_term=short_, long_term=long_, gap_count=2)
broker.strategy_register(tf_strategy)
broker.sizer_register(sizer=r)
matcher = SimulateMatcher()
broker.matcher_register(matcher=matcher)

painter = CandlePainter(mav=(short_, long_))
broker.painter_register(painter)

code_list = remove_index()
code = code_list.sample(n=1).iloc[0].code

pdata1 = gm.get_dayBar_by_mongo(code="sz.300359", start_date="2018-05-01")
engine.feed(pdata1)
engine.start()
import matplotlib.pyplot as plt

plt.set_loglevel("warning")
painter.draw_live()
