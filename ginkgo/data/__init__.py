import os
import sys
from ginkgo import GCONF
from ginkgo.data.drivers import GinkgoClickhouse


CLICKDRIVER = GinkgoClickhouse(
    user=GCONF.CLICKUSER,
    pwd=GCONF.CLICKPWD,
    host=GCONF.CLICKHOST,
    port=GCONF.CLICKPORT,
    db=GCONF.CLICKDB,
)
