import unittest
import datetime
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.backtest.bar import Bar


class BarTest(unittest.TestCase):
    """
    UnitTest for bar.
    """

    # Init
    # Change
    # Amplitude

    def __init__(self, *args, **kwargs) -> None:
        super(BarTest, self).__init__(*args, **kwargs)

    def test_BarInit_OK(self):
        print("")
        gl.logger.warn("Bar初始化 测试开始.")
        params = [
            {
                "code": "sh.0000001",
                "open": 10.2,
                "high": 11,
                "low": 9.45,
                "close": 10,
                "volume": 100,
                "timestamp": "2020-01-01 02:02:32",
            },
            {
                "code": "sh.0000001",
                "open": 10,
                "high": 11.1,
                "low": 9.6,
                "close": 9.4,
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
            },
        ]
        for i in range(len(params)):
            item = params[i]
            b = Bar(
                item["code"],
                item["open"],
                item["high"],
                item["low"],
                item["close"],
                item["volume"],
                item["timestamp"],
            )
        gl.logger.warn("Bar初始化 测试完成.")

    def test_BarChange_OK(self):
        print("")
        gl.logger.warn("Bar Change 测试开始.")
        params = [
            {
                "code": "sh.0000001",
                "open": 10.2,
                "high": 11,
                "low": 9.45,
                "close": 10,
                "volume": 100,
                "timestamp": "2020-01-01 02:02:32",
            },
            {
                "code": "sh.0000001",
                "open": 10,
                "high": 11.1,
                "low": 9.6,
                "close": 9.4,
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
            },
            {
                "code": "sh.0000001",
                "open": 10,
                "high": 11.1,
                "low": 9.6,
                "close": 11.4,
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
            },
            {
                "code": "sh.0000001",
                "open": 10,
                "high": 11.1,
                "low": 9.6,
                "close": 11,
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
            },
        ]
        result = [-0.2, -0.6, 1.4, 1]
        for i in range(len(params)):
            item = params[i]
            r = result[i]
            b = Bar(
                item["code"],
                item["open"],
                item["high"],
                item["low"],
                item["close"],
                item["volume"],
                item["timestamp"],
            )
            self.assertEqual(b.chg, result[i])
        gl.logger.warn("Bar Change 测试完成.")

    def test_BarAmplitude_OK(self):
        print("")
        gl.logger.warn("Bar Amplitude 测试开始.")
        params = [
            {
                "code": "sh.0000001",
                "open": 10.2,
                "high": 11,
                "low": 9.45,
                "close": 10,
                "volume": 100,
                "timestamp": "2020-01-01 02:02:32",
            },
            {
                "code": "sh.0000001",
                "open": 10,
                "high": 11.1,
                "low": 9.6,
                "close": 9.4,
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
            },
            {
                "code": "sh.0000001",
                "open": 10,
                "high": 11.1,
                "low": 9.6,
                "close": 11.4,
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
            },
            {
                "code": "sh.0000001",
                "open": 10,
                "high": 11.6,
                "low": 9.6,
                "close": 11,
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
            },
        ]
        result = [1.55, 1.5, 1.5, 2]
        for i in range(len(params)):
            item = params[i]
            r = result[i]
            b = Bar(
                item["code"],
                item["open"],
                item["high"],
                item["low"],
                item["close"],
                item["volume"],
                item["timestamp"],
            )
            self.assertEqual(b.amplitude, result[i])
        gl.logger.warn("Bar Amplitude 测试完成.")
