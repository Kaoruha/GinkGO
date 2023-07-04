import unittest
import time
from ginkgo.libs import GLOG
from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse
from ginkgo.libs.ginkgo_conf import GCONF


class ClickDriverTest(unittest.TestCase):
    """
    UnitTest for Clickhouse Driver.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(ClickDriverTest, self).__init__(*args, **kwargs)
        self.dev = False

    def test_ClickDriver_Init(self) -> None:
        time.sleep(GCONF.HEARTBEAT)

        db = GinkgoClickhouse(
            user=GCONF.CLICKUSER,
            pwd=GCONF.CLICKPWD,
            host=GCONF.CLICKHOST,
            port=GCONF.CLICKPORT,
            db=GCONF.CLICKDB,
        )
        r = None
        try:
            r = db.is_table_exsists("Shouldnotbethere")
        except Exception as e:
            GLOG.logger.error(
                "Clickhouse Connection Failed. Please check your config file. And make sure the docker status."
            )

        self.assertEqual(False, r)
