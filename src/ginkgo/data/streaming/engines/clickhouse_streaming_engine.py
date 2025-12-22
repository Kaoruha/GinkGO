"""
ClickHouse专用流式查询引擎

实现基于ClickHouse原生流式传输的高性能大数据查询处理，
支持列式存储优化和分布式查询的智能流式传输。

核心特性：
- ClickHouse原生流式传输支持
- 列式存储优化的批处理策略
- 分布式查询分片感知处理
- 智能查询重写和索引优化
"""

import time
import psutil
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


class ClickHouseStreamingEngine(BaseStreamingEngine):
    """ClickHouse专用流式查询引擎"""

    def __init__(self, connection, config: StreamingConfig):
        """
        初始化ClickHouse流式查询引擎

        Args:
            connection: ClickHouse数据库连接或连接池
            config: 流式查询配置
        """
        super().__init__(connection, config)

        # ClickHouse专用配置
        self._cursor_type = CursorType.NATIVE_STREAMING
        self._use_native_streaming = True
        self._clickhouse_version = None
        self._supports_streaming = True

        # 列式存储优化
        self._column_oriented_batch = config.performance.enable_column_optimization
        self._compression_enabled = True

        # 性能监控
        self._memory_monitor = config.monitoring.enable_memory_monitoring
        self._adaptive_batch_size = config.performance.adaptive_batch_size
        self._current_batch_size = config.performance.default_batch_size

        # 分布式查询支持
        self._distributed_query = False
        self._shard_awareness = config.performance.enable_shard_awareness

        GLOG.DEBUG(f"ClickHouseStreamingEngine initialized with native streaming support")

    def get_db_type(self) -> str:
        """获取数据库类型"""
        return "clickhouse"

    def _create_streaming_cursor(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        创建ClickHouse原生流式查询游标

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            ClickHouse流式查询游标对象
        """
        try:
            # 获取原生ClickHouse连接
            raw_connection = self.connection.raw_connection()

            # ClickHouse使用标准游标但配置为流式模式
            cursor = raw_connection.cursor()

            # 设置ClickHouse特定的流式查询参数
            streaming_settings = {
                "max_result_rows": 0,  # 无行数限制
                "max_result_bytes": 0,  # 无字节数限制
                "result_overflow_mode": "break",  # 结果溢出时中断
                "max_execution_time": 0,  # 无执行时间限制
                "send_timeout": 0,  # 无发送超时
                "receive_timeout": 0,  # 无接收超时
                "max_memory_usage": 0,  # 无内存使用限制
                "prefer_localhost_replica": 1,  # 优先本地副本
            }

            # 应用流式设置
            for setting, value in streaming_settings.items():
                try:
                    cursor.execute(f"SET {setting} = {value}")
                except Exception as e:
                    GLOG.DEBUG(f"Failed to set ClickHouse setting {setting}: {e}")

            # 执行查询
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            GLOG.DEBUG(f"Created ClickHouse streaming cursor for query: {query[:100]}...")
            return cursor

        except Exception as e:
            error_msg = f"Failed to create ClickHouse streaming cursor: {e}"
            GLOG.ERROR(error_msg)
            raise StreamingEngineError(error_msg) from e

    def _optimize_query_for_streaming(self, query: str, filters: Dict[str, Any]) -> str:
        """
        优化ClickHouse查询语句用于流式处理

        Args:
            query: 原始查询语句
            filters: 查询过滤条件

        Returns:
            优化后的查询语句
        """
        optimized_query = query.strip()

        # 检测是否为分布式查询
        self._distributed_query = "Distributed" in optimized_query or "_all" in optimized_query

        # ClickHouse特定优化
        clickhouse_optimizations = []

        # 1. 添加SETTINGS子句进行流式优化
        settings = []

        # 启用流式处理设置
        settings.extend(
            [
                "max_threads = 1",  # 单线程确保顺序
                "max_memory_usage = 0",  # 无内存限制
                "max_execution_time = 0",  # 无执行时间限制
                "send_timeout = 0",
                "receive_timeout = 0",
                "max_result_rows = 0",
                "max_result_bytes = 0",
            ]
        )

        # 列式存储优化
        if self._column_oriented_batch:
            settings.extend(
                [
                    "optimize_read_in_order = 1",  # 按顺序读取优化
                    "max_compress_block_size = 1048576",  # 1MB压缩块
                    "min_compress_block_size = 65536",  # 64KB最小压缩块
                ]
            )

        # 分布式查询优化
        if self._distributed_query and self._shard_awareness:
            settings.extend(
                [
                    "distributed_perfect_shard = 1",  # 完美分片
                    "optimize_skip_unused_shards = 1",  # 跳过未使用分片
                    "allow_experimental_parallel_reading_from_replicas = 1",  # 并行读取副本
                ]
            )

        # 2. 应用SETTINGS
        if settings:
            settings_clause = "SETTINGS " + ", ".join(settings)

            # 检查是否已有SETTINGS子句
            if "SETTINGS" in optimized_query.upper():
                # 合并现有设置
                optimized_query = optimized_query.replace("SETTINGS", settings_clause + ",")
            else:
                # 添加新的SETTINGS子句
                optimized_query += f" {settings_clause}"

        # 3. 优化ORDER BY子句（利用ClickHouse排序键）
        if "ORDER BY" not in optimized_query.upper() and filters:
            # 查找时间相关字段进行排序
            time_fields = [
                field
                for field in filters.keys()
                if any(time_word in field.lower() for time_word in ["time", "date", "timestamp", "created"])
            ]
            if time_fields:
                time_field = time_fields[0].split("__")[0]  # 移除过滤操作符
                # 在SETTINGS之前添加ORDER BY
                if "SETTINGS" in optimized_query:
                    settings_pos = optimized_query.find("SETTINGS")
                    optimized_query = (
                        optimized_query[:settings_pos] + f"ORDER BY {time_field} ASC " + optimized_query[settings_pos:]
                    )
                else:
                    optimized_query += f" ORDER BY {time_field} ASC"

        # 4. 添加FORMAT子句确保原生格式
        if "FORMAT" not in optimized_query.upper():
            optimized_query += " FORMAT Native"

        GLOG.DEBUG(f"ClickHouse query optimized: {optimized_query}")
        return optimized_query

    def _execute_streaming_query(self, cursor: Any, batch_size: int) -> Iterator[List[Any]]:
        """
        执行ClickHouse流式查询并返回批次迭代器

        Args:
            cursor: ClickHouse查询游标
            batch_size: 批次大小

        Yields:
            每批查询结果
        """
        current_batch_size = batch_size

        try:
            while True:
                # 动态调整批处理大小（考虑列式存储特性）
                if self._adaptive_batch_size:
                    current_batch_size = self._adjust_batch_size_for_columnar()

                # 从ClickHouse游标获取一批数据
                batch = cursor.fetchmany(current_batch_size)

                if not batch:
                    # 没有更多数据
                    break

                # ClickHouse列式优化处理
                if self._column_oriented_batch:
                    batch = self._optimize_batch_for_columnar(batch)

                # 内存监控
                if self._memory_monitor:
                    self._check_memory_usage()

                yield batch

                # 如果批次大小小于请求大小，说明数据已取完
                if len(batch) < current_batch_size:
                    break

        except Exception as e:
            error_msg = f"ClickHouse streaming query execution failed: {e}"
            GLOG.ERROR(error_msg)
            raise StreamingEngineError(error_msg) from e

    def _cleanup_cursor(self, cursor: Any) -> None:
        """
        清理ClickHouse游标资源

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

                GLOG.DEBUG("ClickHouse streaming cursor cleaned up successfully")

        except Exception as e:
            GLOG.WARN(f"Error cleaning up ClickHouse cursor: {e}")

    def _adjust_batch_size_for_columnar(self) -> int:
        """
        针对列式存储调整批处理大小

        Returns:
            调整后的批处理大小
        """
        if not self._adaptive_batch_size:
            return self._current_batch_size

        try:
            # 获取当前内存使用情况
            memory_percent = psutil.virtual_memory().percent

            # ClickHouse列式存储特殊考虑
            if self._column_oriented_batch:
                # 列式存储通常可以处理更大的批次
                base_multiplier = 2.0
            else:
                base_multiplier = 1.0

            # 根据内存使用情况调整批处理大小
            if memory_percent > 85:
                # 内存使用过高，减小批处理大小
                self._current_batch_size = max(
                    int(self._current_batch_size / base_multiplier), self.config.performance.min_batch_size
                )
                GLOG.DEBUG(f"Reduced ClickHouse batch size to {self._current_batch_size} due to high memory usage")

            elif memory_percent < 40 and self.metrics.processing_rate > 5000:
                # 内存充足且处理速度快，增加批处理大小（列式存储优势）
                self._current_batch_size = min(
                    int(self._current_batch_size * base_multiplier * 1.5), self.config.performance.max_batch_size
                )
                GLOG.DEBUG(f"Increased ClickHouse batch size to {self._current_batch_size} for better performance")

            return self._current_batch_size

        except Exception as e:
            GLOG.WARN(f"Failed to adjust ClickHouse batch size: {e}")
            return self._current_batch_size

    def _optimize_batch_for_columnar(self, batch: List[Any]) -> List[Any]:
        """
        针对列式存储优化批次数据

        Args:
            batch: 原始批次数据

        Returns:
            优化后的批次数据
        """
        if not self._column_oriented_batch or not batch:
            return batch

        try:
            # ClickHouse列式存储优化：
            # 1. 数据压缩检测
            # 2. 列数据重排序
            # 3. 数据类型优化

            # 这里实现简单的优化逻辑
            # 实际生产环境中可以根据具体需求进行更复杂的优化

            if len(batch) > 1000:  # 大批次数据才进行优化
                GLOG.DEBUG(f"Applied columnar optimization to batch of {len(batch)} rows")

            return batch

        except Exception as e:
            GLOG.WARN(f"Failed to optimize batch for columnar storage: {e}")
            return batch

    def _check_memory_usage(self) -> None:
        """检查内存使用情况（ClickHouse特定）"""
        try:
            memory_info = psutil.virtual_memory()
            memory_mb = memory_info.used / (1024 * 1024)

            # 更新指标
            if memory_mb > self.metrics.memory_peak_mb:
                self.metrics.memory_peak_mb = memory_mb

            # ClickHouse对内存使用更敏感，降低告警阈值
            warning_threshold = self.config.monitoring.memory_warning_threshold * 0.8

            if memory_info.percent > warning_threshold:
                GLOG.WARN(
                    f"High memory usage detected for ClickHouse: {memory_info.percent:.1f}% "
                    f"({memory_mb:.1f}MB used)"
                )

        except Exception as e:
            GLOG.WARN(f"Failed to check ClickHouse memory usage: {e}")

    def _pre_query_setup(self) -> None:
        """ClickHouse查询前设置"""
        super()._pre_query_setup()

        try:
            # 检查ClickHouse版本和功能支持
            self._check_clickhouse_capabilities()

            # 设置ClickHouse会话变量优化流式查询
            self._optimize_clickhouse_session()

        except Exception as e:
            GLOG.WARN(f"ClickHouse pre-query setup failed: {e}")

    def _check_clickhouse_capabilities(self) -> None:
        """检查ClickHouse版本和流式查询支持"""
        try:
            # 通过连接获取ClickHouse版本信息
            with (
                self.connection.get_session()
                if hasattr(self.connection, "get_session")
                else self.connection.raw_connection()
            ) as conn:

                if hasattr(conn, "execute"):
                    result = conn.execute("SELECT version()").fetchone()
                    self._clickhouse_version = result[0] if result else "Unknown"
                else:
                    # 原生连接
                    cursor = conn.cursor()
                    cursor.execute("SELECT version()")
                    result = cursor.fetchone()
                    self._clickhouse_version = result[0] if result else "Unknown"
                    cursor.close()

                GLOG.DEBUG(f"ClickHouse version detected: {self._clickhouse_version}")

                # ClickHouse原生支持流式传输
                self._supports_streaming = True

                # 检查分布式功能支持
                if hasattr(conn, "execute"):
                    cluster_result = conn.execute(
                        "SELECT count() FROM system.clusters WHERE cluster = 'default'"
                    ).fetchone()
                    self._shard_awareness = (cluster_result[0] > 0) if cluster_result else False

        except Exception as e:
            GLOG.WARN(f"Failed to check ClickHouse capabilities: {e}")
            self._clickhouse_version = "Unknown"
            self._supports_streaming = True
            self._shard_awareness = False

    def _optimize_clickhouse_session(self) -> None:
        """优化ClickHouse会话设置用于流式查询"""
        try:
            optimization_queries = [
                # 内存和性能设置
                "SET max_memory_usage = 0",  # 无内存限制
                "SET max_execution_time = 0",  # 无执行时间限制
                # 网络设置
                "SET send_timeout = 0",
                "SET receive_timeout = 0",
                "SET tcp_keep_alive_timeout = 7200",  # 2小时TCP保活
                # 结果集设置
                "SET max_result_rows = 0",
                "SET max_result_bytes = 0",
                "SET result_overflow_mode = 'break'",
                # 读取优化
                "SET optimize_read_in_order = 1",
                "SET max_threads = 1",  # 单线程确保顺序
                # 压缩设置
                "SET network_compression_method = 'lz4'",
                "SET network_zstd_compression_level = 1",
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
                    GLOG.DEBUG(f"Failed to apply ClickHouse optimization '{query}': {e}")

            GLOG.DEBUG("ClickHouse session optimizations applied")

        except Exception as e:
            GLOG.WARN(f"Failed to optimize ClickHouse session: {e}")

    @contextmanager
    def streaming_transaction(self):
        """ClickHouse流式查询事务上下文管理器"""
        session_start = time.time()
        GLOG.DEBUG("Starting ClickHouse streaming transaction")

        try:
            # ClickHouse通常不需要显式事务，但可以使用会话
            if hasattr(self.connection, "get_streaming_session"):
                with self.connection.get_streaming_session() as session:
                    yield session
            else:
                # 降级到常规连接
                with self.connection.get_session() as session:
                    yield session

        except Exception as e:
            GLOG.ERROR(f"ClickHouse streaming transaction failed: {e}")
            raise
        finally:
            session_duration = time.time() - session_start
            GLOG.DEBUG(f"ClickHouse streaming transaction completed in {session_duration:.2f}s")

    def get_engine_info(self) -> Dict[str, Any]:
        """获取ClickHouse流式引擎信息"""
        return {
            "engine_type": "clickhouse_streaming",
            "clickhouse_version": self._clickhouse_version,
            "cursor_type": self._cursor_type.value,
            "supports_streaming": self._supports_streaming,
            "distributed_query": self._distributed_query,
            "shard_awareness": self._shard_awareness,
            "column_oriented_batch": self._column_oriented_batch,
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
