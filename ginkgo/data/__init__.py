import os
import sys
from ginkgo import GCONF
from ginkgo.data.drivers import GinkgoClickhouse


DBDRIVER = None


if GCONF.DBDRIVER == "clickhouse":
    DBDRIVER = GinkgoClickhouse(
        user=GCONF.CLICKUSER,
        pwd=GCONF.CLICKPWD,
        host=GCONF.CLICKHOST,
        port=GCONF.CLICKPORT,
        db=GCONF.CLICKDB,
    )
else:
    pass
