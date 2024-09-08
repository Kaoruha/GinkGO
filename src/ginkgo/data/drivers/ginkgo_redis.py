import redis
import time
from ginkgo.libs.ginkgo_logger import GLOG, GinkgoLogger

data_logger = GinkgoLogger("ginkgo_data", "ginkgo_data.log")


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

    def connect(self) -> None:
        for i in range(self.max_try):
            try:
                self._pool = redis.ConnectionPool(
                    host=self._host, port=self._port, decode_responses=None
                )  # host是redis主机，需要redis服务端和客户端都起着 redis默认端口是6379
                self._redis = redis.Redis(connection_pool=self._pool)
                GLOG.DEBUG("Connect to redis succeed.")
            except Exception as e:
                print(e)
                GLOG.DEBUG(f"Connect to Redis Failed {i+1}/{self.max_try} times.")
                time.sleep(2 * (i + 1))

    @property
    def redis(self):
        if self._redis is None:
            self.connect()
        return self._redis
