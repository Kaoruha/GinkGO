"""
回测引擎测试案例
"""

from src.backtest.sizer.risk_avg_sizer import RiskAVGSizer
from src.backtest.events import EventType
from src.backtest.broker.T_1_broker import T1Broker
from src.backtest.event_engine import EventEngine
from src.data.ginkgo_mongo import ginkgo_mongo as gm
from src.backtest.matcher.simulate_matcher import SimulateMatcher
from src.backtest.strategy.trend_follow import TrendFollow
from src.backtest.strategy.profit_loss_limit import ProfitLossLimit
from src.util.stock_filter import remove_index
from src.backtest.painter.candle import CandlePainter
import matplotlib.pyplot as plt

# 引擎事件注册
engine = EventEngine()
broker = T1Broker(init_capital=100000, engine=engine)
engine.register(EventType.Market, broker.market_handler)
engine.register(EventType.Signal, broker.signal_handler)
engine.register(EventType.Order, broker.order_handler)
engine.register(EventType.Fill, broker.fill_handler)
# tf_strategy = TestStrategy()
# 策略挂载
short_ = 20
long_ = 43
tf_strategy = TrendFollow(short_term=short_, long_term=long_, gap_count=3)
broker.strategy_register(tf_strategy)

pll_strategy = ProfitLossLimit(limit=(20, 10))
broker.strategy_register(pll_strategy)

# 开仓策略
r = RiskAVGSizer(base_factor=500)
broker.sizer_register(sizer=r)

# 模拟撮合
matcher = SimulateMatcher()
broker.matcher_register(matcher=matcher)

# 绘图
painter = CandlePainter(mav=(short_, long_))
broker.painter_register(painter)

# 准备数据
code_list = remove_index()
code = code_list.sample(n=1).iloc[0].code
pdata1 = gm.get_dayBar_by_mongo(code=code, start_date="2020-07-01")

# 喂数据，启动
engine.feed(pdata1)
engine.start()

plt.set_loglevel("warning")
painter.draw_live()
