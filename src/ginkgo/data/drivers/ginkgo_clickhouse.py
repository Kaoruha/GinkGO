from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, scoped_session

from ...libs import GLOG, GinkgoLogger
from ...libs.utils.health_check import check_clickhouse_ready
from .base_driver import DatabaseDriverBase


class GinkgoClickhouse(DatabaseDriverBase):
    """ClickHouse数据库驱动 - 继承DatabaseDriverBase"""

    # 类级别的ClickHouse专用logger，避免重复创建
    _clickhouse_logger = None

    def __init__(self, user: str, pwd: str, host: str, port: str, db: str, *args, **kwargs) -> None:
        # 调用基类初始化
        super().__init__("ClickHouse")

        self._user = user
        self._pwd = pwd
        self._host = host
        self._port = port
        self._db = db
        self._echo = kwargs.get("echo", False)
        self._connect_timeout = kwargs.get("connect_timeout", 10)
        self._read_timeout = kwargs.get("read_timeout", 10)

        # 添加ClickHouse专用logger (关闭控制台输出)
        if GinkgoClickhouse._clickhouse_logger is None:
            GinkgoClickhouse._clickhouse_logger = GinkgoLogger(
                logger_name="ginkgo_clickhouse",
                file_names=["clickhouse.log"],
                console_log=False,  # 关闭控制台输出，避免重复打印
            )
        self.add_logger(GinkgoClickhouse._clickhouse_logger)

        # 初始化时自动创建引擎（保持向后兼容）
        self._engine = self._create_engine()
        self._session_factory = scoped_session(sessionmaker(bind=self.engine))

    def _get_uri(self) -> str:
        """获取ClickHouse连接URI"""
        return (
            f"clickhouse://{self._user}:{self._pwd}@"
            f"{self._host}:{self._port}/{self._db}"
            f"?connect_timeout={self._connect_timeout}"
            f"&read_timeout={self._read_timeout}"
        )

    def _create_engine(self):
        """创建ClickHouse引擎"""
        return create_engine(
            self._get_uri(),
            echo=self._echo,
            future=True,
            pool_recycle=7200,  # ClickHouse适合更长的连接回收时间
            pool_size=10,  # ClickHouse通常需要较少的连接
            pool_timeout=60,  # 分析查询可能需要更长时间
            max_overflow=5,  # 较小的溢出连接数
            pool_pre_ping=True,  # 连接前预检查
        )

    def _health_check_query(self) -> str:
        """ClickHouse健康检查查询"""
        return "SELECT 1"

    def _get_streaming_uri(self) -> str:
        """🆕 获取ClickHouse流式查询专用连接URI - 优化参数用于大数据流式处理"""
        return (
            f"clickhouse://{self._user}:{self._pwd}@"
            f"{self._host}:{self._port}/{self._db}"
            f"?connect_timeout={self._connect_timeout * 3}"  # 流式查询使用更长超时
            f"&read_timeout={self._read_timeout * 20}"  # 大数据查询长时间读取支持
            f"&send_receive_timeout=0"  # 禁用发送接收超时，适合长时间查询
            f"&max_execution_time=0"  # 禁用执行时间限制
            f"&stream_mode=1"  # 启用流式模式
        )

    def _create_streaming_engine(self):
        """🆕 创建ClickHouse流式查询专用引擎 - 原生流式传输支持"""
        return create_engine(
            self._get_streaming_uri(),
            echo=self._echo,
            future=True,
            # 🔥 ClickHouse流式查询专用连接池配置
            pool_recycle=14400,  # 4小时连接回收（大数据查询可能很长）
            pool_size=3,  # 更小的连接池，专用于流式查询
            pool_timeout=120,  # 更长的获取连接超时
            max_overflow=1,  # 最小溢出连接数
            pool_pre_ping=True,
            # 🔥 ClickHouse流式查询专用参数
            execution_options={
                "stream_results": True,  # 启用结果流式传输
                "compiled_cache": {},  # 查询编译缓存
                "autocommit": False,  # 流式查询禁用自动提交
            },
            connect_args={
                "settings": {
                    "max_memory_usage": "0",  # 禁用内存使用限制
                    "max_execution_time": "0",  # 禁用执行时间限制
                    "send_timeout": "0",  # 禁用发送超时
                    "receive_timeout": "0",  # 禁用接收超时
                    "max_result_rows": "0",  # 禁用结果行数限制
                    "result_overflow_mode": "break",  # 结果溢出时中断
                    "max_threads": "1",  # 单线程处理确保顺序
                    "prefer_localhost_replica": "1",  # 优先本地副本
                }
            }
        )

    def health_check(self) -> bool:
        """使用专门的ClickHouse健康检查"""
        try:
            # 首先使用现有的health_check模块进行连接检查
            if not check_clickhouse_ready(self._host, int(self._port)):
                self.log("WARNING", "ClickHouse connection check failed")
                return False

            # 再进行SQL查询验证
            return super().health_check()
        except Exception as e:
            self.log("WARNING", f"ClickHouse health check failed: {e}")
            return False

    @property
    def engine(self):
        """
        获取数据库引擎（向后兼容）
        Returns:
            DB Engine.
        """
        return self._engine

    @property
    def session(self):
        """
        获取数据库会话（向后兼容）
        Returns:
            DB Session.
        """
        return self._session_factory()

    def remove_session(self) -> None:
        """移除会话（向后兼容）"""
        self._session_factory.remove()
