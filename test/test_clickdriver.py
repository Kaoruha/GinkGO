import unittest
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse
from ginkgo.libs.ginkgo_conf import GINKGOCONF


class ClickDriverTest(unittest.TestCase):
    """
    UnitTest for Clickhouse Driver.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(ClickDriverTest, self).__init__(*args, **kwargs)

    def test_EventBaseInit_OK(self) -> None:
        print("")
        gl.logger.warn("ClickDriver 初始化 测试开始.")

        db = GinkgoClickhouse(
            user=GINKGOCONF.CLICKUSER,
            pwd=GINKGOCONF.CLICKPWD,
            host=GINKGOCONF.CLICKHOST,
            port=GINKGOCONF.CLICKPORT,
            db=GINKGOCONF.CLICKDB,
        )
        r = None
        try:
            r = db.is_table_exsists("Shouldnotbethere")
        except Exception as e:
            gl.logger.error(
                "Clickhouse Connection Failed. Please check your config file. And make sure the docker status."
            )

        self.assertEqual(False, r)

        gl.logger.warn("ClickDriver 初始化 测试完成.")
