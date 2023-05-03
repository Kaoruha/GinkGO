import unittest
import datetime
from time import sleep
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.bar import Bar
from ginkgo.enums import FREQUENCY_TYPES
from ginkgo.libs.ginkgo_conf import GINKGOCONF


class BarTest(unittest.TestCase):
    """
    UnitTest for bar.
    """

    # Init
    # Change
    # Amplitude

    def __init__(self, *args, **kwargs) -> None:
        super(BarTest, self).__init__(*args, **kwargs)
        self.sim_code = "unittest_simcode"
        self.sim_open = 10.1
        self.sim_high = 11
        self.sim_low = 9
        self.sim_close = 9.51
        self.sim_volume = 1991231
        self.sim_fre = FREQUENCY_TYPES.DAY
        self.sim_date = datetime.datetime.now()

    def sim_ins(self) -> Bar:
        b = Bar(
            self.sim_code,
            self.sim_open,
            self.sim_high,
            self.sim_low,
            self.sim_close,
            self.sim_volume,
            self.sim_fre,
            self.sim_date,
        )
        return b

    def test_BarInit(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        result = True
        params = [
            {
                "code": "sh.0000001",
                "open": 10.2,
                "high": 11,
                "low": 9.45,
                "close": 10,
                "volume": 100,
                "frequency": FREQUENCY_TYPES.DAY,
                "timestamp": "2020-01-01 02:02:32",
            },
            {
                "code": "sh.0000001",
                "open": 10,
                "high": 11.1,
                "low": 9.6,
                "close": 9.4,
                "volume": 10022,
                "frequency": FREQUENCY_TYPES.DAY,
                "timestamp": datetime.datetime.now(),
            },
        ]
        try:
            for i in range(len(params)):
                item = params[i]
                b = Bar(
                    item["code"],
                    item["open"],
                    item["high"],
                    item["low"],
                    item["close"],
                    item["volume"],
                    item["frequency"],
                    item["timestamp"],
                )
        except Exception as e:
            result = False

        self.assertEqual(result, True)

    def test_BarCode(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.sim_ins()
        self.assertEqual(r.code, self.sim_code)

    def test_BarOpen(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.sim_ins()
        self.assertEqual(r.open, self.sim_open)

    def test_BarHigh(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.sim_ins()
        self.assertEqual(r.high, self.sim_high)

    def test_BarLow(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.sim_ins()
        self.assertEqual(r.low, self.sim_low)

    def test_BarClose(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.sim_ins()
        self.assertEqual(r.close, self.sim_close)

    def test_BarFrequency(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.sim_ins()
        self.assertEqual(r.frequency, self.sim_fre)

    def test_BarTime(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.sim_ins()
        self.assertEqual(r.timestamp, self.sim_date)

    def test_BarChange(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.sim_ins()
        r_expect = round(self.sim_close - self.sim_open, 2)
        self.assertEqual(r.chg, r_expect)

    def test_BarAmplitude(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.sim_ins()
        self.assertEqual(r.amplitude, self.sim_high - self.sim_low)
