from ginkgo.data.models.model_daybar import MDaybar
from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES
from ginkgo.backtest.bar import Bar
import datetime


a = MDaybar()
print(a)
a.set("testcode", SOURCE_TYPES.SIM, 2.2, 3.3, 1.1, 2.1, 200, datetime.datetime.now())
print(a)

b = Bar(
    code="aaa",
    open_=222,
    high=222,
    low=222,
    close=222,
    volume=2222,
    frequency=FREQUENCY_TYPES.DAY,
    timestamp=datetime.datetime.now(),
)
print(b)
print(FREQUENCY_TYPES.DAY)
a.set(b)
print(a)
