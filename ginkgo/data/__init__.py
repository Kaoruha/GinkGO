import os
import sys
import inspect
import importlib
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.data.drivers.ginkgo_clickhouse import GinkgoClickhouse


DBDRIVER = None


if GINKGOCONF.DBDRIVER == "clickhouse":
    DBDRIVER = GinkgoClickhouse(
        user=GINKGOCONF.CLICKUSER,
        pwd=GINKGOCONF.CLICKPWD,
        host=GINKGOCONF.CLICKHOST,
        port=GINKGOCONF.CLICKPORT,
        db=GINKGOCONF.CLICKDB,
    )
else:
    pass
