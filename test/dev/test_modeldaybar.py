import unittest
import datetime
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.backtest.bar import Bar
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.data.models.model_daybar import MDaybar
from ginkgo.enums import SOURCE_TYPES


class ModelDaybarTest(unittest.TestCase):
    """
    UnitTest for Daybar.
    """

    # Init
    # set data from bar
    # store in to ginkgodata
    # query from ginkgodata

    def __init__(self, *args, **kwargs) -> None:
        super(ModelDaybarTest, self).__init__(*args, **kwargs)

    def test_DaybarInit_OK(self) -> None:
        print("")
        gl.logger.warn("Daybar 初始化 测试开始.")
        params = [
            {
                "code": "testcode",
                "source": SOURCE_TYPES.BAOSTOCK,
                "open": 2,
                "high": 2.444444,
                "low": 1,
                "close": 1.999,
                "volume": 23331,
                "timestamp": datetime.datetime.now(),
            }
        ]
        for i in params:
            o = MDaybar()
            o.update_data(
                i["code"],
                i["source"],
                i["open"],
                i["high"],
                i["low"],
                i["close"],
                i["volume"],
                i["timestamp"],
            )
            print(o)
        gl.logger.warn("Daybar 初始化 测试完成.")

    def test_DaybarDataset_OK(self) -> None:
        print("")
        gl.logger.warn("Daybar DataSet 测试开始.")
        gl.logger.warn("Daybar DataSet 测试完成.")

    def test_DaybarInsert_OK(self) -> None:
        print("")
        gl.logger.warn("Daybar Insert 测试开始.")
        gl.logger.warn("Daybar Insert 测试完成.")

    def test_DaybarQuery_OK(self) -> None:
        print("")
        gl.logger.warn("Daybar Query 测试开始.")
        gl.logger.warn("Daybar Query 测试完成.")
