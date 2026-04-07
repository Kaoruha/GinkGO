# Upstream: 数据层容器(containers.py), Worker系统, 偏差检测模块, RedisService
# Downstream: redis-py, GinkgoLogger, 装饰器(retry/time_logger)
# Role: Redis缓存驱动，封装连接池和基础键值操作，支持自动重连






import redis
import time
from ginkgo.libs import GLOG, GinkgoLogger, retry, time_logger

data_logger = GinkgoLogger("ginkgo_data", ["ginkgo_data.log"])


class GinkgoRedis(object):
    def __init__(self, host: str, port: int) -> None:
        self._pool = None
        self._redis = None
        self._host = host
        self._port = port
        self._max_try = 5

    @property
    def max_try(self) -> int:
        return self._max_try

    @time_logger(threshold=0.5)
    @retry
    def connect(self) -> None:
        self._pool = redis.ConnectionPool(
            host=self._host, port=self._port, decode_responses=None
        )  # host是redis主机，需要redis服务端和客户端都起着 redis默认端口是6379
        self._redis = redis.Redis(connection_pool=self._pool)
        GLOG.DEBUG("Connect to redis succeed.")

    @property
    def redis(self):
        if self._redis is None:
            self.connect()
        return self._redis

