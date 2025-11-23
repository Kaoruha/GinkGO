"""
MySQL专用流式查询引擎

实现基于MySQL服务器端游标的高性能流式查询处理，
支持大数据集的内存优化流式传输和智能批处理。

核心特性：
- 服务器端游标(SSCursor)实现真正的流式处理
- 自适应批处理大小优化
- 连接异常自动恢复机制
- MySQL查询优化器集成
"""

import time
import psutil
import pymysql
from typing import Any, Dict, List, Iterator, Optional, Union
from contextlib import contextmanager

try:
    from ginkgo.libs import GLOG

    _has_ginkgo_logger = True
except ImportError:
    _has_ginkgo_logger = False
    import logging

    GLOG = logging.getLogger(__name__)

from ginkgo.data.streaming.engines.base_streaming_engine import BaseStreamingEngine, CursorType, StreamingMetrics
from ginkgo.data.streaming import StreamingState, StreamingEngineError
from ginkgo.data.streaming.config import StreamingConfig


class MySQLStreamingEngine(BaseStreamingEngine):
    """MySQL专用流式查询引擎"""

    def __init__(self, connection, config: StreamingConfig):
        """
        初始化MySQL流式查询引擎

        Args:
            connection: MySQL数据库连接或连接池
            config: 流式查询配置
        """
        super().__init__(connection, config)

        # MySQL专用配置
        self._cursor_type = CursorType.SERVER_SIDE
        self._use_buffered = False
        self._mysql_version = None
        self._supports_streaming = True

        # 性能监控
        self._memory_monitor = config.monitoring.enable_memory_monitoring
        self._adaptive_batch_size = config.performance.adaptive_batch_size
        self._current_batch_size = config.performance.default_batch_size

        GLOG.DEBUG(f"MySQLStreamingEngine initialized with cursor_type: {self._cursor_type}")

    def get_db_type(self) -> str:
        """获取数据库类型"""
        return "mysql"

    def _create_streaming_cursor(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        创建MySQL服务器端游标用于流式查询

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            MySQL服务器端游标对象
        """
        try:
            # 获取原生MySQL连接
            raw_connection = self.connection.raw_connection()

            # 创建服务器端游标 (SSCursor)
            cursor = raw_connection.cursor(pymysql.cursors.SSCursor)

            # 设置查询缓冲模式
            if hasattr(cursor, "_defer_warnings"):
                cursor._defer_warnings = True

            # 执行查询
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            GLOG.DEBUG(f"Created MySQL server-side cursor for query: {query[:100]}...")
            return cursor

        except Exception as e:
            error_msg = f"Failed to create MySQL streaming cursor: {e}"
            GLOG.ERROR(error_msg)
            raise StreamingEngineError(error_msg) from e

    def _optimize_query_for_streaming(self, query: str, filters: Dict[str, Any]) -> str:
        """
        优化MySQL查询语句用于流式处理

        Args:
            query: 原始查询语句
            filters: 查询过滤条件

        Returns:
            优化后的查询语句
        """
        optimized_query = query.strip()

        # 添加MySQL特定的优化提示
        mysql_hints = []

        # 1. 强制使用索引扫描（如果有时间范围过滤）
        if any(key.endswith("__gte") or key.endswith("__lte") for key in filters.keys()):
            mysql_hints.append("USE INDEX FOR ORDER BY")

        # 2. 启用流式结果集
        mysql_hints.append("SQL_BUFFER_RESULT")

        # 3. 添加查询优化器提示
        if "ORDER BY" in optimized_query.upper():
            # 对于有序查询，使用文件排序
            mysql_hints.append("SQL_BIG_RESULT")

        # 4. 应用优化提示
        if mysql_hints and "SELECT" in optimized_query.upper():
            select_pos = optimized_query.upper().find("SELECT")
            if select_pos >= 0:
                hints_str = f"/*+ {' '.join(mysql_hints)} */"
                optimized_query = (
                    optimized_query[: select_pos + 6] + " " + hints_str + " " + optimized_query[select_pos + 6 :]
                )

        # 5. 确保查询结果有序（便于断点续传）
        if "ORDER BY" not in optimized_query.upper() and filters:
            # 尝试找到时间字段进行排序
            time_fields = [
                field
                for field in filters.keys()
                if any(time_word in field.lower() for time_word in ["time", "date", "created", "updated"])
            ]
            if time_fields:
                time_field = time_fields[0].split("__")[0]  # 移除过滤操作符
                optimized_query += f" ORDER BY {time_field} ASC"

        GLOG.DEBUG(f"MySQL query optimized: {optimized_query}")
        return optimized_query

    def _execute_streaming_query(self, cursor: Any, batch_size: int) -> Iterator[List[Any]]:
        """
        执行MySQL流式查询并返回批次迭代器

        Args:
            cursor: MySQL服务器端游标
            batch_size: 批次大小

        Yields:
            每批查询结果
        """
        current_batch_size = batch_size

        try:
            while True:
                # 动态调整批处理大小
                if self._adaptive_batch_size:
                    current_batch_size = self._adjust_batch_size()

                # 从游标获取一批数据
                batch = cursor.fetchmany(current_batch_size)

                if not batch:
                    # 没有更多数据
                    break

                # 内存监控
                if self._memory_monitor:
                    self._check_memory_usage()

                yield batch

                # 如果批次大小小于请求大小，说明数据已取完
                if len(batch) < current_batch_size:
                    break

        except Exception as e:
            error_msg = f"MySQL streaming query execution failed: {e}"
            GLOG.ERROR(error_msg)
            raise StreamingEngineError(error_msg) from e

    def _cleanup_cursor(self, cursor: Any) -> None:
        """
        清理MySQL游标资源

        Args:
            cursor: 需要清理的游标
        """
        try:
            if cursor:
                # 关闭游标
                cursor.close()

                # 关闭底层连接
                if hasattr(cursor, "connection") and cursor.connection:
                    cursor.connection.close()

                GLOG.DEBUG("MySQL streaming cursor cleaned up successfully")

        except Exception as e:
            GLOG.WARNING(f"Error cleaning up MySQL cursor: {e}")

    def _adjust_batch_size(self) -> int:
        """
        自适应调整批处理大小

        Returns:
            调整后的批处理大小
        """
        if not self._adaptive_batch_size:
            return self._current_batch_size

        try:
            # 获取当前内存使用情况
            memory_percent = psutil.virtual_memory().percent

            # 根据内存使用情况调整批处理大小
            if memory_percent > 80:
                # 内存使用过高，减小批处理大小
                self._current_batch_size = max(self._current_batch_size // 2, self.config.performance.min_batch_size)
                GLOG.DEBUG(f"Reduced batch size to {self._current_batch_size} due to high memory usage")

            elif memory_percent < 50 and self.metrics.processing_rate > 1000:
                # 内存充足且处理速度快，增加批处理大小
                self._current_batch_size = min(
                    int(self._current_batch_size * 1.5), self.config.performance.max_batch_size
                )
                GLOG.DEBUG(f"Increased batch size to {self._current_batch_size} for better performance")

            return self._current_batch_size

        except Exception as e:
            GLOG.WARNING(f"Failed to adjust batch size: {e}")
            return self._current_batch_size

    def _check_memory_usage(self) -> None:
        """检查内存使用情况"""
        try:
            memory_info = psutil.virtual_memory()
            memory_mb = memory_info.used / (1024 * 1024)

            # 更新指标
            if memory_mb > self.metrics.memory_peak_mb:
                self.metrics.memory_peak_mb = memory_mb

            # 内存告警
            if memory_info.percent > self.config.monitoring.memory_warning_threshold:
                GLOG.WARNING(f"High memory usage detected: {memory_info.percent:.1f}% " f"({memory_mb:.1f}MB used)")

        except Exception as e:
            GLOG.WARNING(f"Failed to check memory usage: {e}")

    def _pre_query_setup(self) -> None:
        """MySQL查询前设置"""
        super()._pre_query_setup()

        try:
            # 检查MySQL版本和功能支持
            self._check_mysql_capabilities()

            # 设置MySQL会话变量优化流式查询
            self._optimize_mysql_session()

        except Exception as e:
            GLOG.WARNING(f"MySQL pre-query setup failed: {e}")

    def _check_mysql_capabilities(self) -> None:
        """检查MySQL版本和流式查询支持"""
        try:
            # 通过连接获取MySQL版本信息
            with (
                self.connection.get_session()
                if hasattr(self.connection, "get_session")
                else self.connection.raw_connection()
            ) as conn:

                if hasattr(conn, "execute"):
                    result = conn.execute("SELECT VERSION()").fetchone()
                    self._mysql_version = result[0] if result else "Unknown"
                else:
                    # 原生连接
                    cursor = conn.cursor()
                    cursor.execute("SELECT VERSION()")
                    result = cursor.fetchone()
                    self._mysql_version = result[0] if result else "Unknown"
                    cursor.close()

                GLOG.DEBUG(f"MySQL version detected: {self._mysql_version}")

                # 检查是否支持服务器端游标
                major_version = int(self._mysql_version.split(".")[0])
                self._supports_streaming = major_version >= 5

                if not self._supports_streaming:
                    GLOG.WARNING(f"MySQL version {self._mysql_version} may not fully support streaming")

        except Exception as e:
            GLOG.WARNING(f"Failed to check MySQL capabilities: {e}")
            self._mysql_version = "Unknown"
            self._supports_streaming = True  # 假设支持

    def _optimize_mysql_session(self) -> None:
        """优化MySQL会话设置用于流式查询"""
        try:
            optimization_queries = [
                # 设置查询缓存
                "SET SESSION query_cache_type = OFF",  # 禁用查询缓存以节省内存
                # 设置排序缓冲区
                "SET SESSION sort_buffer_size = 2097152",  # 2MB排序缓冲区
                # 设置读取缓冲区
                "SET SESSION read_buffer_size = 131072",  # 128KB读取缓冲区
                # 设置网络缓冲区
                "SET SESSION net_buffer_length = 32768",  # 32KB网络缓冲区
                # 设置最大允许的包大小
                "SET SESSION max_allowed_packet = 67108864",  # 64MB
            ]

            # 应用优化设置
            for query in optimization_queries:
                try:
                    with (
                        self.connection.get_session()
                        if hasattr(self.connection, "get_session")
                        else self.connection.raw_connection()
                    ) as conn:
                        if hasattr(conn, "execute"):
                            conn.execute(query)
                        else:
                            cursor = conn.cursor()
                            cursor.execute(query)
                            cursor.close()

                except Exception as e:
                    GLOG.DEBUG(f"Failed to apply MySQL optimization '{query}': {e}")

            GLOG.DEBUG("MySQL session optimizations applied")

        except Exception as e:
            GLOG.WARNING(f"Failed to optimize MySQL session: {e}")

    @contextmanager
    def streaming_transaction(self):
        """MySQL流式查询事务上下文管理器"""
        session_start = time.time()
        GLOG.DEBUG("Starting MySQL streaming transaction")

        try:
            # 获取流式查询专用连接
            if hasattr(self.connection, "get_streaming_session"):
                with self.connection.get_streaming_session() as session:
                    # 设置事务隔离级别（适合流式查询）
                    session.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                    session.begin()

                    yield session

                    session.commit()
            else:
                # 降级到常规连接
                with self.connection.get_session() as session:
                    yield session

        except Exception as e:
            GLOG.ERROR(f"MySQL streaming transaction failed: {e}")
            raise
        finally:
            session_duration = time.time() - session_start
            GLOG.DEBUG(f"MySQL streaming transaction completed in {session_duration:.2f}s")

    def get_engine_info(self) -> Dict[str, Any]:
        """获取MySQL流式引擎信息"""
        return {
            "engine_type": "mysql_streaming",
            "mysql_version": self._mysql_version,
            "cursor_type": self._cursor_type.value,
            "supports_streaming": self._supports_streaming,
            "current_batch_size": self._current_batch_size,
            "adaptive_batch_size": self._adaptive_batch_size,
            "memory_monitoring": self._memory_monitor,
            "state": self.state.value,
            "metrics": {
                "total_processed": self.metrics.total_processed,
                "processing_rate": self.metrics.processing_rate,
                "memory_peak_mb": self.metrics.memory_peak_mb,
                "elapsed_time": self.metrics.elapsed_time,
            },
        }
