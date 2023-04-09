import unittest
import datetime
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.backtest.tick import Tick


class TickTest(unittest.TestCase):
    """
    UnitTest for tick.
    """

    # Init
    def __init__(self, *args, **kwargs) -> None:
        super(TickTest, self).__init__(*args, **kwargs)

    def test_TickInit_OK(self) -> None:
        print("")
        gl.logger.warn("Tick初始化 测试开始.")
        params = [
            {
                "code": "sh.0000001",
                "price": 10.2,
                "volume": 100,
                "timestamp": "2020-01-01 02:02:32",
            },
            {
                "code": "sh.0000001",
                "price": 10,
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
            },
        ]
        for i in range(len(params)):
            item = params[i]
            code = item["code"]
            price = item["price"]
            volume = item["volume"]
            timestamp = item["timestamp"]
            t = Tick(code, price, volume, timestamp)
        gl.logger.warn("Tick初始化 测试完成.")
