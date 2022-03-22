"""
Author: Kaoru
Date: 2022-03-20 23:37:02
LastEditTime: 2022-03-22 11:40:23
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/for_test.py
What goes around comes around.
"""
# from src.backtest.broker.base_broker import BaseBroker
# from src.backtest.event_engine import EventEngine
# from src.backtest.selector.base_selector import BaseSelector

# e = EventEngine(heartbeat=.001)
# b = BaseBroker(engine=e, name='myBroker', start_date='2007-12-01', end_date='2021-12-14')
# b.selector_register(BaseSelector())
# e.register_next_day(b.next_day)
# e.start()
from src.backtest.bar import Bar

b = Bar()
print(b)
print(b.interval)
b.interval = 1
print(b.interval)
