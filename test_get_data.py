import datetime
import numpy as np
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo_server.backtest.event_engine import EventEngine
from ginkgo_server.backtest.broker.single_daily_broker import SingleDailyBroker
from ginkgo_server.backtest.enums import EventType
from ginkgo_server.data.stock.baostock_data import bao_instance
from ginkgo_server.backtest.strategy.moving_average import MovingAverageStrategy
from ginkgo_server.backtest.strategy.target_profit import TargetProfit
from ginkgo_server.backtest.strategy.stop_loss import StopLoss
from ginkgo_server.backtest.matcher.simulate_matcher import SimulateMatcher
from ginkgo_server.backtest.sizer.all_in_one import AllInOne


if __name__ == "__main__":
    bao_instance.login()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    df = gm.query_stock(
        code="sz.000725",
        start_date="2000-11-01",
        end_date=today,
        frequency="d",
        adjust_flag=3,
    )
    df.fillna(0)
    # s = df.iloc[3026]['turn']

    df = df.replace("", 0)
    print(df.iloc[3026])
    # for i in range(df.shape[0]):
    #     if df.iloc[i]['turn'] == '':
    #         print(i)
