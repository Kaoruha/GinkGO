import os
import sys
import inspect
import importlib
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse
from ginkgo.data.sources.ginkgo_baostock import GinkgoBaoStock


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
