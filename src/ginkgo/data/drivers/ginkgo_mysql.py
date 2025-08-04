import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from ...libs import GLOG, GinkgoLogger
from ...libs.utils.health_check import check_mysql_ready
from .base_driver import DatabaseDriverBase


class GinkgoMysql(DatabaseDriverBase):
    """MySQL数据库驱动 - 继承DatabaseDriverBase"""

    # 类级别的MySQL专用logger，避免重复创建
    _mysql_logger = None

    def __init__(self, user: str, pwd: str, host: str, port: str, db: str, *args, **kwargs) -> None:
        # 调用基类初始化
        super().__init__("MySQL")

        self._user = user
        self._pwd = pwd
        self._host = host
        self._port = port
        self._db = db
        self._echo = kwargs.get("echo", False)
        self._connect_timeout = kwargs.get("connect_timeout", 2)
        self._read_timeout = kwargs.get("read_timeout", 4)

        # 添加MySQL专用logger (关闭控制台输出)
        if GinkgoMysql._mysql_logger is None:
            GinkgoMysql._mysql_logger = GinkgoLogger(
                logger_name="ginkgo_mysql", file_names=["mysql.log"], console_log=False  # 关闭控制台输出，避免重复打印
            )
        self.add_logger(GinkgoMysql._mysql_logger)

        # 初始化时自动创建引擎（保持向后兼容）
        self._engine = self._create_engine()
        self._session_factory = scoped_session(sessionmaker(bind=self.engine))

    def _get_uri(self) -> str:
        """获取MySQL连接URI"""
        return (
            f"mysql+pymysql://{self._user}:{self._pwd}@"
            f"{self._host}:{self._port}/{self._db}"
            f"?connect_timeout={self._connect_timeout}"
            f"&read_timeout={self._read_timeout}"
        )

    def _create_engine(self):
        """创建MySQL引擎"""
        return create_engine(
            self._get_uri(),
            echo=self._echo,
            future=True,
            pool_recycle=3600,  # 连接回收时间
            pool_size=20,  # 连接池大小
            pool_timeout=30,  # 获取连接超时时间
            max_overflow=10,  # 最大溢出连接数
            pool_pre_ping=True,  # 连接前预检查
        )

    def _health_check_query(self) -> str:
        """MySQL健康检查查询"""
        return "SELECT 1"

    def health_check(self) -> bool:
        """使用专门的MySQL健康检查"""
        try:
            # 首先使用现有的health_check模块进行连接检查
            if not check_mysql_ready(self._host, int(self._port), self._user, self._pwd):
                self.log("WARNING", "MySQL connection check failed")
                return False

            # 再进行SQL查询验证
            return super().health_check()
        except Exception as e:
            self.log("WARNING", f"MySQL health check failed: {e}")
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
