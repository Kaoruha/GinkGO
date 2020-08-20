from ginkgo.data.data_portal import data_portal
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.broker.single_daily_broker import SingleDailyBroker
from ginkgo.backtest.event import *
from ginkgo.backtest.strategy.moving_average import MovingAverageStrategy

if __name__ == '__main__':
    df = data_portal.query_stock(code='sh.000001', start_date='1990-01-01', end_date='2020-08-01', frequency='d',
                                 adjust_flag=2)
    # df['ma_5'] = df['close'].rolling(5, min_periods=1).mean()
    # print(df.iloc[0])

    backtest_engine = EventEngine()
    my_broker = SingleDailyBroker(name='my_broker')
    backtest_engine.register(DailyEvent, my_broker.daily_handlers)
    backtest_engine.feed(df)
    backtest_engine.start()
