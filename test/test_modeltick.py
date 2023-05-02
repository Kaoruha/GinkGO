import unittest
import time
import datetime
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.tick import Tick
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.data.models.model_tick import MTick
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs.ginkgo_conf import GINKGOCONF


class ModelTickTest(unittest.TestCase):
    """
    UnitTest for ModelTick.
    """

    # Init
    # set data from dataframe
    # store in to ginkgodata
    # query from ginkgodata

    def __init__(self, *args, **kwargs) -> None:
        super(ModelTickTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "source": SOURCE_TYPES.BAOSTOCK,
                "code": "testcode",
                "price": 2,
                "volume": 23331,
                "timestamp": datetime.datetime.now(),
            }
        ]

    def test_ModelTickInit_OK(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            item = MTick()
            item.set(
                i["code"],
                i["price"],
                i["volume"],
                i["timestamp"],
            )
            item.set_source(SOURCE_TYPES.BAOSTOCK)

    def test_ModelTickInsert_OK(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)

        GINKGODATA.drop_table(MTick)
        GINKGODATA.create_table(MTick)
        o = MTick()
        GINKGODATA.add(o)
        GINKGODATA.commit()

    def test_ModelTickBatchInsert_OK(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)

        GINKGODATA.drop_table(MTick)
        GINKGODATA.create_table(MTick)
        s = []

        for i in range(10):
            o = MTick()
            s.append(o)
            # o.dire = 2

        GINKGODATA.add_all(s)
        GINKGODATA.commit()

    def test_ModelTickQuery_OK(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)

        GINKGODATA.drop_table(MTick)
        GINKGODATA.create_table(MTick)
        o = MTick()
        GINKGODATA.add(o)
        GINKGODATA.commit()
        r = GINKGODATA.session.query(MTick).first()
