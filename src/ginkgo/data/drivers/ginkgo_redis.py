import redis
from ginkgo.libs.ginkgo_logger import GLOG


class GinkgoRedis(object):
    def __init__(self, host: str, port: int) -> None:
        self._pool = None
        self._redis = None
        self._host = host
        self._port = port

        self.__connect()

    def __connect(self) -> None:
        self._pool = redis.ConnectionPool(
            host=self._host, port=self._port, decode_responses=None
        )  # host是redis主机，需要redis服务端和客户端都起着 redis默认端口是6379
        self._redis = redis.Redis(connection_pool=self._pool)
        GLOG.INFO("Connect to redis succeed.")

    @property
    def redis(self):
        if self._redis is None:
            self.__connect()
        return self._redis
