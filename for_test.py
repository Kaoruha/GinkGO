from ginkgo.data.data_engine import DataEngine
from ginkgo.backtest.event_engine import EventEngine
import datetime
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm

d = DataEngine()
e = EventEngine()
d.set_event_engine(e)


a = gm.get_all_stockcode_by_mongo().sample(1).code.values[0]
print(a)
a = "bj.871642"
df = d.get_daybar(code=a, date="2020-01-21")
