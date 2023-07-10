import unittest
import time
import datetime
import pandas as pd
from ginkgo.libs import GLOG
from ginkgo.backtest.signals import Signal
from ginkgo.data.models import MSignal
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class SignalTest(unittest.TestCase):
    """
    UnitTest for Signal.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(SignalTest, self).__init__(*args, **kwargs)
        self.dev = False
        self.params = [
            {
                "code": "sh.0000001",
                "timestamp": "2020-01-01 02:02:32",
                "direction": DIRECTION_TYPES.LONG,
                "source": SOURCE_TYPES.SIM,
            },
        ]

    def test_Signal_Init(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = False
        try:
            s = Signal()
            result = True
        except Exception as e:
            pass

        self.assertEqual(result, True)

    def test_Signal_Set(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        for item in self.params:
            s = Signal()
            s.set(
                item["code"],
                item["direction"],
                item["timestamp"],
            )
            s.set_source(SOURCE_TYPES.TEST)
            self.assertEqual(s.code, item["code"])
            self.assertEqual(s.direction, item["direction"])

    def test_Signal_SetFromDataFrame(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        for item in self.params:
            data = {
                "code": item["code"],
                "direction": item["direction"],
                "timestamp": item["timestamp"],
                "source": item["source"],
                "uuid": "",
            }
            df = pd.Series(data)
            s = Signal()
            s.set(df)
            self.assertEqual(s.code, item["code"])
            self.assertEqual(s.direction, item["direction"])
            self.assertEqual(s.source, item["source"])
