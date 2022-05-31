import unittest
from ginkgo.config.setting import VERSION
from ginkgo.libs import GINKGOLOGGER as gl


class VersionTest(unittest.TestCase):
    pass

    def test_GetSignal_OK(self):
        print("")
        gl.logger.critical(f"查看版本")
        gl.logger.warning(VERSION)
        gl.logger.critical(f"查看版本")
        gl.logger.warning(VERSION)
        gl.logger.critical(f"查看版本")
