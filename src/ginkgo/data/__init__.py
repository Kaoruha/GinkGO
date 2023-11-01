from ginkgo.data.drivers import GinkgoClickhouse, GinkgoMysql, GinkgoRedis
from ginkgo.libs.ginkgo_conf import GCONF

REDISDRIVER = GinkgoRedis(GCONF.REDISHOST, GCONF.REDISPORT).redis
CLICKDRIVER = GinkgoClickhouse(
    user=GCONF.CLICKUSER,
    pwd=GCONF.CLICKPWD,
    host=GCONF.CLICKHOST,
    port=GCONF.CLICKPORT,
    db=GCONF.CLICKDB,
)
MYSQLDRIVER = GinkgoMysql(
    user=GCONF.MYSQLUSER,
    pwd=GCONF.MYSQLPWD,
    host=GCONF.MYSQLHOST,
    port=GCONF.MYSQLPORT,
    db=GCONF.MYSQLDB,
)
