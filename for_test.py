from src.backtest.broker.base_broker import BaseBroker
from src.backtest.event_engine import EventEngine
from src.backtest.selector.base_selector import BaseSelector

e = EventEngine(heartbeat=.001)
b = BaseBroker(engine=e, name='myBroker', start_date='2007-12-01', end_date='2021-12-14')
b.selector_register(BaseSelector())
e.register_next_day(b.next_day)

e.start()