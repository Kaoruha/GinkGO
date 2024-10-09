import unittest
import time

from ginkgo.data.drivers.ginkgo_mysql import GinkgoMysql
from ginkgo.libs.ginkgo_conf import GCONF


class MysqlDriverTest(unittest.TestCase):
    """
    UnitTest for Mysql Driver.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(MysqlDriverTest, self).__init__(*args, **kwargs)

    def test_MysqlDriver_Init(self) -> None:
        driver = GinkgoMysql(
            user=GCONF.MYSQLUSER,
            pwd=GCONF.MYSQLPWD,
            host=GCONF.MYSQLHOST,
            port=GCONF.MYSQLPORT,
            db=GCONF.MYSQLDB,
        )
        self.assertNotEqual(None, driver)
