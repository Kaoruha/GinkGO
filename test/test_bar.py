import unittest
import datetime
from time import sleep
from ginkgo.libs import GLOG
from ginkgo.backtest.bar import Bar
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
from ginkgo.libs.ginkgo_conf import GCONF


class BarTest(unittest.TestCase):
    """
    UnitTest for Bar.
    """

    # Init
    # Change
    # Amplitude

    def __init__(self, *args, **kwargs) -> None:
        super(BarTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "sim_code": "unittest_simcode",
                "sim_open": 10.1,
                "sim_high": 11,
                "sim_low": 9,
                "sim_close": 9.51,
                "sim_volume": 1991231,
                "sim_fre": FREQUENCY_TYPES.DAY,
                "sim_timestamp": "2020-01-01 02:02:32",
                "sim_source": SOURCE_TYPES.TEST,
            },
            {
                "sim_code": "sh.0000001",
                "sim_open": 10,
                "sim_high": 11.1,
                "sim_low": 9.6,
                "sim_close": 9.4,
                "sim_volume": 10022,
                "sim_fre": FREQUENCY_TYPES.DAY,
                "sim_timestamp": datetime.datetime.now(),
                "sim_source": SOURCE_TYPES.SINA,
            },
        ]

    def test_Bar_Init(self) -> None:
        sleep(GCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                b = Bar(
                    i["sim_code"],
                    i["sim_open"],
                    i["sim_high"],
                    i["sim_low"],
                    i["sim_close"],
                    i["sim_volume"],
                    i["sim_fre"],
                    i["sim_timestamp"],
                )
                b.set_source(i["sim_source"])
            except Exception as e:
                result = False
        self.assertEqual(result, True)

    def test_Bar_Set(self) -> None:
        sleep(GCONF.HEARTBEAT)
        for i in self.params:
            b = Bar()
            b.set(
                i["sim_code"],
                i["sim_open"],
                i["sim_high"],
                i["sim_low"],
                i["sim_close"],
                i["sim_volume"],
                i["sim_fre"],
                i["sim_timestamp"],
            )
            b.set_source(i["sim_source"])
            self.assertEqual(b.code, i["sim_code"])
            self.assertEqual(b.open, i["sim_open"])
            self.assertEqual(b.high, i["sim_high"])
            self.assertEqual(b.low, i["sim_low"])
            self.assertEqual(b.close, i["sim_close"])
            self.assertEqual(b.source, i["sim_source"])

    def test_Bar_SetFromDataFrame(self) -> None:
        # TODO
        pass

    def test_Bar_Code(self) -> None:
        sleep(GCONF.HEARTBEAT)
        for i in self.params:
            b = Bar(
                i["sim_code"],
                i["sim_open"],
                i["sim_high"],
                i["sim_low"],
                i["sim_close"],
                i["sim_volume"],
                i["sim_fre"],
                i["sim_timestamp"],
            )
            b.set_source(i["sim_source"])
            self.assertEqual(b.code, i["sim_code"])

    def test_Bar_Open(self) -> None:
        sleep(GCONF.HEARTBEAT)
        for i in self.params:
            b = Bar(
                i["sim_code"],
                i["sim_open"],
                i["sim_high"],
                i["sim_low"],
                i["sim_close"],
                i["sim_volume"],
                i["sim_fre"],
                i["sim_timestamp"],
            )
            b.set_source(i["sim_source"])
            self.assertEqual(b.open, i["sim_open"])

    def test_Bar_High(self) -> None:
        sleep(GCONF.HEARTBEAT)
        for i in self.params:
            b = Bar(
                i["sim_code"],
                i["sim_open"],
                i["sim_high"],
                i["sim_low"],
                i["sim_close"],
                i["sim_volume"],
                i["sim_fre"],
                i["sim_timestamp"],
            )
            b.set_source(i["sim_source"])
            self.assertEqual(b.high, i["sim_high"])

    def test_Bar_Low(self) -> None:
        sleep(GCONF.HEARTBEAT)
        for i in self.params:
            b = Bar(
                i["sim_code"],
                i["sim_open"],
                i["sim_high"],
                i["sim_low"],
                i["sim_close"],
                i["sim_volume"],
                i["sim_fre"],
                i["sim_timestamp"],
            )
            b.set_source(i["sim_source"])
            self.assertEqual(b.low, i["sim_low"])

    def test_Bar_Close(self) -> None:
        sleep(GCONF.HEARTBEAT)
        for i in self.params:
            b = Bar(
                i["sim_code"],
                i["sim_open"],
                i["sim_high"],
                i["sim_low"],
                i["sim_close"],
                i["sim_volume"],
                i["sim_fre"],
                i["sim_timestamp"],
            )
            b.set_source(i["sim_source"])
            self.assertEqual(b.close, i["sim_close"])

    def test_Bar_Frequency(self) -> None:
        sleep(GCONF.HEARTBEAT)
        for i in self.params:
            b = Bar(
                i["sim_code"],
                i["sim_open"],
                i["sim_high"],
                i["sim_low"],
                i["sim_close"],
                i["sim_volume"],
                i["sim_fre"],
                i["sim_timestamp"],
            )
            b.set_source(i["sim_source"])
            self.assertEqual(b.frequency, i["sim_fre"])

    def test_Bar_Change(self) -> None:
        sleep(GCONF.HEARTBEAT)
        for i in self.params:
            b = Bar(
                i["sim_code"],
                i["sim_open"],
                i["sim_high"],
                i["sim_low"],
                i["sim_close"],
                i["sim_volume"],
                i["sim_fre"],
                i["sim_timestamp"],
            )
            b.set_source(i["sim_source"])
            r_expect = round(i["sim_close"] - i["sim_open"], 2)
            self.assertEqual(b.chg, r_expect)

    def test_Bar_Amplitude(self) -> None:
        sleep(GCONF.HEARTBEAT)
        for i in self.params:
            b = Bar(
                i["sim_code"],
                i["sim_open"],
                i["sim_high"],
                i["sim_low"],
                i["sim_close"],
                i["sim_volume"],
                i["sim_fre"],
                i["sim_timestamp"],
            )
            b.set_source(i["sim_source"])
            self.assertEqual(b.amplitude, i["sim_high"] - i["sim_low"])

    def test_Bar_Source(self) -> None:
        sleep(GCONF.HEARTBEAT)
        for i in self.params:
            b = Bar(
                i["sim_code"],
                i["sim_open"],
                i["sim_high"],
                i["sim_low"],
                i["sim_close"],
                i["sim_volume"],
                i["sim_fre"],
                i["sim_timestamp"],
            )
            b.set_source(i["sim_source"])
            self.assertEqual(b.source, i["sim_source"])
