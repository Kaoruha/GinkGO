import unittest
import time
import datetime
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.backtest.bar import Bar
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.data.models.model_daybar import MDaybar
from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES
from ginkgo.libs.ginkgo_conf import GINKGOCONF


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
        self.params = [
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

    def test_ModelDaybarInit_OK(self) -> None:
        print("")
        gl.logger.warn("ModelDaybar 初始化 测试开始.")
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            o = MDaybar()

        gl.logger.warn("ModelDaybar 初始化 测试完成.")

    def test_ModelDaybarSetFromData_OK(self) -> None:
        print("")
        gl.logger.warn("ModelDaybar SetFromData 测试开始.")
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            o = MDaybar()
            o.set(
                i["code"],
                i["open"],
                i["high"],
                i["low"],
                i["close"],
                i["volume"],
                i["timestamp"],
            )
            o.set_source(i["source"])
            print(o)
        gl.logger.warn("ModelDaybar SetFromData 测试完成.")

    def test_ModelDaybarSetFromDataFrame_OK(self) -> None:
        print("")
        gl.logger.warn("ModelDaybar SetFromDataFrame 测试开始.")
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            o = MDaybar()
            b = Bar(
                i["code"],
                i["open"],
                i["high"],
                i["low"],
                i["close"],
                i["volume"],
                FREQUENCY_TYPES.DAY,
                datetime.datetime.now(),
            )
            o.set(b.to_dataframe)
            o.set_source(SOURCE_TYPES.SINA)
            print(o)
        gl.logger.warn("ModelDaybar SetFromDataFrame 测试完成.")

    def test_ModelDaybarInsert_OK(self) -> None:
        print("")
        gl.logger.warn("ModelDaybar Insert 测试开始.")
        time.sleep(GINKGOCONF.HEARTBEAT)

        GINKGODATA.drop_table(MDaybar)
        GINKGODATA.create_table(MDaybar)
        o = MDaybar()
        GINKGODATA.add(o)
        GINKGODATA.commit()
        gl.logger.warn("ModelDaybar Insert 测试完成.")

    def test_ModelDaybarBatchInsert_OK(self) -> None:
        print("")
        gl.logger.warn("ModelDaybar BatchInsert 测试开始.")
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MDaybar)
        GINKGODATA.create_table(MDaybar)
        s = []

        for i in range(10):
            o = MDaybar()
            s.append(o)
            # o.dire = 2

        GINKGODATA.add_all(s)
        GINKGODATA.commit()
        gl.logger.warn("ModelDaybar BatchInsert 测试完成.")

    def test_ModelDaybarQuery_OK(self) -> None:
        print("")
        gl.logger.warn("ModelDaybar Query 测试开始.")
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MDaybar)
        GINKGODATA.create_table(MDaybar)
        o = MDaybar()
        GINKGODATA.add(o)
        GINKGODATA.commit()
        r = GINKGODATA.session.query(MDaybar).first()
        print(r)
        gl.logger.warn("ModelDaybar Query 测试完成.")
