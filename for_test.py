print("halo")

from ginkgo.data.drivers import GinkgoClickhouse
from ginkgo.libs.ginkgo_conf import GCONF


DB = GinkgoClickhouse(
    user=GCONF.CLICKUSER,
    pwd=GCONF.CLICKPWD,
    host=GCONF.CLICKHOST,
    port=GCONF.CLICKPORT,
    db=GCONF.CLICKDB,
)

DB.create_database()
