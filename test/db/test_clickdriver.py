import unittest
from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse
from ginkgo.libs.ginkgo_conf import GCONF


class ClickDriverTest(unittest.TestCase):
    """
    UnitTest for Clickhouse Driver.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(ClickDriverTest, self).__init__(*args, **kwargs)

    def test_ClickDriver_Init(self) -> None:
        driver = GinkgoClickhouse(
            user=GCONF.CLICKUSER,
            pwd=GCONF.CLICKPWD,
            host=GCONF.CLICKHOST,
            port=GCONF.CLICKPORT,
            db=GCONF.CLICKDB,
        )
        self.assertNotEqual(None, driver)
