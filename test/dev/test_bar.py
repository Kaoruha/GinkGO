import unittest
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.backtest.bar import Bar


class BarTest(unittest.TestCase):
    """
    UnitTest for bar.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(BarTest, self).__init__(*args, **kwargs)

    def test_BarInit_OK(self):
        print("")
        gl.logger.warn("Bar初始化测试开始.")
        params = [
            {
                "code": "sh.0000001",
                "open": 10.2,
                "high": 11,
                "low": 9.45,
                "close": 10,
            },
            {
                "code": "sh.0000001",
                "open": 10,
                "high": 11.1,
                "low": 9.6,
                "close": 9.4,
            },
        ]
        for item in params:
            print(item)
        gl.logger.warn("Bar初始化测试完成.")
