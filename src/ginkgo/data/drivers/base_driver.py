# Upstream: All Concrete Database Drivers (GinkgoClickHouse/GinkgoMySQL/GinkgoMongo/GinkgoRedis继承)
# Downstream: sqlalchemy (数据库连接引擎)、GLOG (日志记录)
# Role: BaseDriver基础驱动定义数据库驱动的抽象基类和接口规范数据库操作






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

from ginkgo.libs import time_logger, retry, GLOG, GinkgoLogger, cache_with_expiration


class DatabaseDriverBase(ABC):
    """数据库驱动抽象基类 - 增强支持流式查询连接池"""

    # 类级别的共享database logger，避免重复创建
    _shared_database_logger = None

    def __init__(self, driver_name: str):
        self.driver_name = driver_name
        self._db_type = driver_name.lower()
        self._engine = None
        self._session_factory = None
        
        # 🆕 流式查询专用连接池
        self._streaming_engine = None
        self._streaming_session_factory = None
        self._streaming_enabled = False

        # 连接统计信息
        self._connection_stats = {
            "created_at": time.time(),
            "connections_created": 0,
            "connections_closed": 0,
            "active_connections": 0,
            "last_health_check": 0,
            "health_check_failures": 0,
            # 🆕 流式查询连接统计
            "streaming_connections_created": 0,
            "streaming_connections_closed": 0,
            "active_streaming_connections": 0,
            "streaming_sessions_active": 0,
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

    # ==================== 抽象方法 ====================
    
    @abstractmethod
    def _create_engine(self):
        """子类实现：创建数据库引擎"""
        pass

    @abstractmethod  
    def _create_streaming_engine(self):
        """🆕 子类实现：创建流式查询专用引擎"""
        pass

    @abstractmethod
    def _health_check_query(self) -> str:
        """子类实现：健康检查SQL语句"""
        pass

    @abstractmethod
    def _get_uri(self) -> str:
        """子类实现：获取数据库连接URI"""
        pass
    
    @abstractmethod
    def _get_streaming_uri(self) -> str:
        """🆕 子类实现：获取流式查询专用连接URI"""
        pass

    # ==================== 传统连接池管理 ====================

    @time_logger
    @retry(max_try=3)
    def initialize(self):
        """初始化数据库连接"""
        GLOG.INFO(f"Initializing {self.driver_name} driver...")

        try:
            self._engine = self._create_engine()
            self._session_factory = scoped_session(sessionmaker(bind=self._engine))

            if not self.health_check():
                raise RuntimeError(f"{self.driver_name} health check failed")

            GLOG.INFO(f"{self.driver_name} driver initialized successfully")

        except Exception as e:
            GLOG.ERROR(f"Failed to initialize {self.driver_name}: {e}")
            raise

    # ==================== 🆕 流式查询连接池管理 ====================
    
    @time_logger
    @retry(max_try=3)
    def initialize_streaming(self):
        """初始化流式查询专用连接池"""
        GLOG.INFO(f"Initializing {self.driver_name} streaming connection pool...")
        
        try:
            self._streaming_engine = self._create_streaming_engine()
            self._streaming_session_factory = scoped_session(
                sessionmaker(bind=self._streaming_engine)
            )
            self._streaming_enabled = True
            
            if not self.health_check_streaming():
                raise RuntimeError(f"{self.driver_name} streaming health check failed")
                
            GLOG.INFO(f"{self.driver_name} streaming connection pool initialized successfully")
            
        except Exception as e:
            GLOG.ERROR(f"Failed to initialize {self.driver_name} streaming pool: {e}")
            self._streaming_enabled = False
            raise
    
    def is_streaming_enabled(self) -> bool:
        """检查流式查询是否已启用"""
        return self._streaming_enabled and self._streaming_engine is not None
    
    @contextmanager  
    def get_streaming_session(self):
        """🆕 上下文管理器：流式查询专用会话"""
        if not self.is_streaming_enabled():
            self.initialize_streaming()
            
        if not self.is_streaming_enabled():
            # 降级到常规会话
            self.log("WARNING", "Streaming not available, falling back to regular session")
            with self.get_session() as session:
                yield session
            return
            
        session = None
        try:
            with self._lock:
                self._connection_stats["streaming_connections_created"] += 1
                self._connection_stats["active_streaming_connections"] += 1
                self._connection_stats["streaming_sessions_active"] += 1
                
            session = self._streaming_session_factory()
            GLOG.DEBUG(f"Created streaming session for {self.driver_name}")
            yield session
            session.commit()
            
        except Exception as e:
            if session:
                session.rollback()
            GLOG.ERROR(f"{self.driver_name} streaming session error: {e}")
            raise
        finally:
            if session:
                session.close()
                with self._lock:
                    self._connection_stats["streaming_connections_closed"] += 1
                    self._connection_stats["active_streaming_connections"] -= 1  
                    self._connection_stats["streaming_sessions_active"] -= 1
                    
    def get_streaming_connection(self):
        """🆕 获取流式查询原生连接（用于服务器端游标）"""
        if not self.is_streaming_enabled():
            self.initialize_streaming()
            
        if not self.is_streaming_enabled():
            # 降级到常规连接
            self.log("WARNING", "Streaming not available, falling back to regular connection")
            return self._engine.raw_connection()
            
        try:
            connection = self._streaming_engine.raw_connection()
            with self._lock:
                self._connection_stats["streaming_connections_created"] += 1
                self._connection_stats["active_streaming_connections"] += 1
            return connection
        except Exception as e:
            GLOG.ERROR(f"Failed to get streaming connection for {self.driver_name}: {e}")
            raise

    # ==================== 健康检查 ====================

    @cache_with_expiration(expiration_seconds=300)
    def health_check(self) -> bool:
        """数据库健康检查"""
        try:
            with self.get_session() as session:
                session.execute(text(self._health_check_query()))

            with self._lock:
                self._connection_stats["last_health_check"] = time.time()
                self._connection_stats["health_check_failures"] = 0

            GLOG.DEBUG(f"{self.driver_name} health check passed")
            return True

        except Exception as e:
            with self._lock:
                self._connection_stats["health_check_failures"] += 1

            self.log("WARNING", f"{self.driver_name} health check failed: {e}")
            return False
    
    @cache_with_expiration(expiration_seconds=300)        
    def health_check_streaming(self) -> bool:
        """🆕 流式查询连接池健康检查"""
        if not self.is_streaming_enabled():
            return False
            
        try:
            with self.get_streaming_session() as session:
                session.execute(text(self._health_check_query()))
                
            GLOG.DEBUG(f"{self.driver_name} streaming health check passed")
            return True
            
        except Exception as e:
            self.log("WARNING", f"{self.driver_name} streaming health check failed: {e}")
            return False

    # ==================== 传统会话管理（保持向后兼容）====================

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
            GLOG.ERROR(f"{self.driver_name} session error: {e}")
            raise
        finally:
            if session:
                session.close()
                with self._lock:
                    self._connection_stats["connections_closed"] += 1
                    self._connection_stats["active_connections"] -= 1

    # ==================== 统计和监控 ====================

    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息（包含流式查询统计）"""
        with self._lock:
            stats = self._connection_stats.copy()

        stats["uptime"] = time.time() - stats["created_at"]
        stats["connection_efficiency"] = stats["connections_closed"] / max(stats["connections_created"], 1)
        
        # 🆕 流式查询效率统计
        if stats["streaming_connections_created"] > 0:
            stats["streaming_connection_efficiency"] = (
                stats["streaming_connections_closed"] / stats["streaming_connections_created"]
            )
        else:
            stats["streaming_connection_efficiency"] = 0.0
            
        stats["driver_name"] = self.driver_name
        stats["streaming_enabled"] = self.is_streaming_enabled()

        return stats
    
    def get_streaming_pool_info(self) -> Dict[str, Any]:
        """🆕 获取流式查询连接池详细信息"""
        if not self.is_streaming_enabled():
            return {"enabled": False, "message": "Streaming not initialized"}
            
        try:
            # 尝试获取连接池状态（SQLAlchemy特定）
            pool_status = {}
            if hasattr(self._streaming_engine.pool, 'status'):
                pool_status = self._streaming_engine.pool.status()
            elif hasattr(self._streaming_engine.pool, 'size'):
                pool_status = {
                    "pool_size": self._streaming_engine.pool.size(),
                    "checked_in": getattr(self._streaming_engine.pool, 'checkedin', lambda: 0)(),
                    "checked_out": getattr(self._streaming_engine.pool, 'checkedout', lambda: 0)(),
                }
                
            return {
                "enabled": True,
                "driver_type": self._db_type,
                "engine_info": str(self._streaming_engine.url),
                "pool_status": pool_status,
                "active_sessions": self._connection_stats["streaming_sessions_active"],
                "total_created": self._connection_stats["streaming_connections_created"],
                "total_closed": self._connection_stats["streaming_connections_closed"],
            }
        except Exception as e:
            return {
                "enabled": True,
                "error": f"Failed to get pool info: {e}",
                "active_sessions": self._connection_stats["streaming_sessions_active"],
            }

    # ==================== 向后兼容属性 ====================

    @property
    def engine(self):
        """获取数据库引擎（向后兼容）"""
        if self._engine is None:
            self.initialize()
        return self._engine
    
    @property
    def streaming_engine(self):
        """🆕 获取流式查询引擎"""
        if not self.is_streaming_enabled():
            self.initialize_streaming()
        return self._streaming_engine

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
            
    def remove_streaming_session(self):
        """🆕 移除流式查询会话"""
        if self._streaming_session_factory:
            self._streaming_session_factory.remove()

