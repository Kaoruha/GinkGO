"""
数据库驱动基类
提供统一的数据库连接管理、日志记录、健康检查等功能
"""

import time
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Dict, Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

from ...libs import time_logger, retry, GLOG, GinkgoLogger


class DatabaseDriverBase(ABC):
    """数据库驱动抽象基类"""

    # 类级别的共享database logger，避免重复创建
    _shared_database_logger = None

    def __init__(self, driver_name: str):
        self.driver_name = driver_name
        self._db_type = driver_name.lower()
        self._engine = None
        self._session_factory = None

        # 连接统计信息
        self._connection_stats = {
            "created_at": time.time(),
            "connections_created": 0,
            "connections_closed": 0,
            "active_connections": 0,
            "last_health_check": 0,
            "health_check_failures": 0,
        }
        self._lock = threading.Lock()

        # 初始化logger队列
        self.loggers = []
        self._init_loggers()

    def _init_loggers(self):
        """初始化logger队列"""
        # 1. 添加全局GLOG (保持控制台输出)
        self.add_logger(GLOG)

        # 2. 添加共享的database logger (关闭控制台输出)
        if DatabaseDriverBase._shared_database_logger is None:
            DatabaseDriverBase._shared_database_logger = GinkgoLogger(
                logger_name="ginkgo_database",
                file_names=["database.log"],
                console_log=False,  # 关闭控制台输出，避免重复打印
            )
        self.add_logger(DatabaseDriverBase._shared_database_logger)

    def add_logger(self, logger):
        """添加日志器到队列，避免重复添加同名logger"""
        # 检查是否已存在同名logger
        logger_name = getattr(logger, "logger_name", str(logger))

        for existing_logger in self.loggers:
            existing_name = getattr(existing_logger, "logger_name", str(existing_logger))
            if existing_name == logger_name:
                return  # 已存在同名logger，跳过添加

        # 如果没有同名logger，则添加
        self.loggers.append(logger)

    def log(self, level: str, msg: str):
        """统一的日志输出方法"""
        formatted_msg = f"[{self.driver_name}] {msg}"
        level_method = level.upper()

        for logger in self.loggers:
            try:
                getattr(logger, level_method)(formatted_msg)
            except AttributeError:
                # 兼容不同logger接口
                try:
                    logger.log(level_method, formatted_msg)
                except Exception:
                    pass
            except Exception:
                # 避免logger错误影响主逻辑
                pass

    @abstractmethod
    def _create_engine(self):
        """子类实现：创建数据库引擎"""
        pass

    @abstractmethod
    def _health_check_query(self) -> str:
        """子类实现：健康检查SQL语句"""
        pass

    @abstractmethod
    def _get_uri(self) -> str:
        """子类实现：获取数据库连接URI"""
        pass

    @time_logger
    @retry(max_try=3)
    def initialize(self):
        """初始化数据库连接"""
        self.log("INFO", f"Initializing {self.driver_name} driver...")

        try:
            self._engine = self._create_engine()
            self._session_factory = scoped_session(sessionmaker(bind=self._engine))

            if not self.health_check():
                raise RuntimeError(f"{self.driver_name} health check failed")

            self.log("INFO", f"{self.driver_name} driver initialized successfully")

        except Exception as e:
            self.log("ERROR", f"Failed to initialize {self.driver_name}: {e}")
            raise

    def health_check(self) -> bool:
        """数据库健康检查"""
        try:
            with self.get_session() as session:
                session.execute(text(self._health_check_query()))

            with self._lock:
                self._connection_stats["last_health_check"] = time.time()
                self._connection_stats["health_check_failures"] = 0

            self.log("DEBUG", f"{self.driver_name} health check passed")
            return True

        except Exception as e:
            with self._lock:
                self._connection_stats["health_check_failures"] += 1

            self.log("WARNING", f"{self.driver_name} health check failed: {e}")
            return False

    @contextmanager
    def get_session(self):
        """上下文管理器：自动管理会话生命周期"""
        if self._session_factory is None:
            self.initialize()

        session = None
        try:
            with self._lock:
                self._connection_stats["connections_created"] += 1
                self._connection_stats["active_connections"] += 1

            session = self._session_factory()
            yield session
            session.commit()

        except Exception as e:
            if session:
                session.rollback()
            self.log("ERROR", f"{self.driver_name} session error: {e}")
            raise
        finally:
            if session:
                session.close()
                with self._lock:
                    self._connection_stats["connections_closed"] += 1
                    self._connection_stats["active_connections"] -= 1

    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        with self._lock:
            stats = self._connection_stats.copy()

        stats["uptime"] = time.time() - stats["created_at"]
        stats["connection_efficiency"] = stats["connections_closed"] / max(stats["connections_created"], 1)
        stats["driver_name"] = self.driver_name

        return stats

    @property
    def engine(self):
        """获取数据库引擎（向后兼容）"""
        if self._engine is None:
            self.initialize()
        return self._engine

    @property
    def session(self):
        """获取会话（向后兼容，建议使用get_session上下文管理器）"""
        if self._session_factory is None:
            self.initialize()
        return self._session_factory()

    def remove_session(self):
        """移除会话（向后兼容）"""
        if self._session_factory:
            self._session_factory.remove()
