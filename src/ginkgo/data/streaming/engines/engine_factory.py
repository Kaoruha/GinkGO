"""
流式查询引擎工厂和查询优化器

提供智能引擎选择、查询分析优化和性能监控功能，
自动选择最适合的流式查询引擎并进行查询优化。

核心功能：
- 自动数据库类型检测和引擎选择
- 智能查询分析和优化建议
- 引擎性能监控和切换
- 查询复杂度评估和优化
"""

import re
import time
from typing import Any, Dict, List, Optional, Union, Type
from enum import Enum
from dataclasses import dataclass

try:
    from ginkgo.libs import GLOG

    _has_ginkgo_logger = True
except ImportError:
    _has_ginkgo_logger = False
    import logging

    GLOG = logging.getLogger(__name__)

from .base_streaming_engine import BaseStreamingEngine
from .mysql_streaming_engine import MySQLStreamingEngine
from .clickhouse_streaming_engine import ClickHouseStreamingEngine
from .. import StreamingEngineError
from ..config import StreamingConfig


class DatabaseType(Enum):
    """支持的数据库类型"""

    MYSQL = "mysql"
    CLICKHOUSE = "clickhouse"
    UNKNOWN = "unknown"


@dataclass
class QueryAnalysis:
    """查询分析结果"""

    complexity_score: float  # 查询复杂度评分 (0-100)
    estimated_rows: Optional[int]  # 预估返回行数
    has_joins: bool  # 是否包含JOIN
    has_subqueries: bool  # 是否包含子查询
    has_aggregations: bool  # 是否包含聚合函数
    has_order_by: bool  # 是否有排序
    has_group_by: bool  # 是否有分组
    time_range_filter: bool  # 是否有时间范围过滤
    indexed_filters: List[str]  # 可能使用索引的过滤条件
    optimization_suggestions: List[str]  # 优化建议


@dataclass
class EnginePerformance:
    """引擎性能指标"""

    engine_type: str
    avg_query_time: float
    success_rate: float
    memory_efficiency: float
    throughput_rate: float
    last_updated: float


class QueryOptimizer:
    """查询优化器"""

    def __init__(self):
        self.optimization_rules = {
            DatabaseType.MYSQL: self._get_mysql_optimization_rules(),
            DatabaseType.CLICKHOUSE: self._get_clickhouse_optimization_rules(),
        }

    def analyze_query(self, query: str, filters: Optional[Dict] = None) -> QueryAnalysis:
        """
        分析查询复杂度和特性

        Args:
            query: SQL查询语句
            filters: 查询过滤条件

        Returns:
            查询分析结果
        """
        query_upper = query.upper()
        filters = filters or {}

        # 基础特性检测
        has_joins = bool(re.search(r"\bJOIN\b", query_upper))
        has_subqueries = bool(re.search(r"\(\s*SELECT\b", query_upper))
        has_aggregations = bool(re.search(r"\b(COUNT|SUM|AVG|MAX|MIN|GROUP_CONCAT)\s*\(", query_upper))
        has_order_by = bool(re.search(r"\bORDER\s+BY\b", query_upper))
        has_group_by = bool(re.search(r"\bGROUP\s+BY\b", query_upper))

        # 时间范围过滤检测
        time_range_filter = any(
            key
            for key in filters.keys()
            if any(time_word in key.lower() for time_word in ["time", "date", "created", "updated"])
        )

        # 索引过滤条件检测
        indexed_filters = [
            key
            for key in filters.keys()
            if any(idx_word in key.lower() for idx_word in ["id", "code", "symbol", "timestamp"])
        ]

        # 复杂度评分计算
        complexity_score = self._calculate_complexity_score(
            has_joins, has_subqueries, has_aggregations, has_order_by, has_group_by, len(filters)
        )

        # 生成优化建议
        optimization_suggestions = self._generate_optimization_suggestions(
            query, has_joins, has_subqueries, has_aggregations, time_range_filter, indexed_filters
        )

        return QueryAnalysis(
            complexity_score=complexity_score,
            estimated_rows=self._estimate_result_rows(query, filters),
            has_joins=has_joins,
            has_subqueries=has_subqueries,
            has_aggregations=has_aggregations,
            has_order_by=has_order_by,
            has_group_by=has_group_by,
            time_range_filter=time_range_filter,
            indexed_filters=indexed_filters,
            optimization_suggestions=optimization_suggestions,
        )

    def _calculate_complexity_score(
        self,
        has_joins: bool,
        has_subqueries: bool,
        has_aggregations: bool,
        has_order_by: bool,
        has_group_by: bool,
        filter_count: int,
    ) -> float:
        """计算查询复杂度评分"""
        score = 10.0  # 基础分数

        if has_joins:
            score += 25.0
        if has_subqueries:
            score += 30.0
        if has_aggregations:
            score += 20.0
        if has_order_by:
            score += 15.0
        if has_group_by:
            score += 20.0

        # 过滤条件复杂度
        score += min(filter_count * 2, 20)

        return min(score, 100.0)

    def _estimate_result_rows(self, query: str, filters: Dict) -> Optional[int]:
        """估算查询结果行数"""
        # 简单的行数估算逻辑
        # 实际生产环境中可以通过统计信息进行更精确的估算

        if not filters:
            return 1000000  # 无过滤条件，假设返回大量数据

        # 根据过滤条件估算
        estimated_rows = 100000  # 基础估算

        # 有ID或精确匹配过滤，大幅减少行数
        if any("id" in key.lower() for key in filters.keys()):
            estimated_rows //= 100

        # 有时间范围过滤
        time_filters = [
            key for key in filters.keys() if any(time_word in key.lower() for time_word in ["time", "date"])
        ]
        if time_filters:
            estimated_rows //= 10

        return max(estimated_rows, 1)

    def _generate_optimization_suggestions(
        self,
        query: str,
        has_joins: bool,
        has_subqueries: bool,
        has_aggregations: bool,
        time_range_filter: bool,
        indexed_filters: List[str],
    ) -> List[str]:
        """生成优化建议"""
        suggestions = []

        if has_joins:
            suggestions.append("考虑优化JOIN条件，确保连接字段有索引")

        if has_subqueries:
            suggestions.append("考虑将子查询重写为JOIN，可能提升性能")

        if has_aggregations and not time_range_filter:
            suggestions.append("聚合查询建议添加时间范围过滤以减少扫描数据量")

        if not indexed_filters:
            suggestions.append("建议添加索引字段过滤条件以提升查询效率")

        if "ORDER BY" not in query.upper() and time_range_filter:
            suggestions.append("建议添加ORDER BY子句利用时间索引优化流式传输")

        return suggestions

    def _get_mysql_optimization_rules(self) -> Dict[str, str]:
        """获取MySQL优化规则"""
        return {
            "use_index_hints": "USE INDEX FOR ORDER BY",
            "force_index_scan": "FORCE INDEX",
            "sql_buffer_result": "SQL_BUFFER_RESULT",
            "sql_big_result": "SQL_BIG_RESULT",
            "straight_join": "STRAIGHT_JOIN",
        }

    def _get_clickhouse_optimization_rules(self) -> Dict[str, str]:
        """获取ClickHouse优化规则"""
        return {
            "optimize_read_in_order": "optimize_read_in_order = 1",
            "distributed_perfect_shard": "distributed_perfect_shard = 1",
            "optimize_skip_unused_shards": "optimize_skip_unused_shards = 1",
            "max_threads": "max_threads = 1",
            "prefer_localhost_replica": "prefer_localhost_replica = 1",
        }


class StreamingEngineFactory:
    """流式查询引擎工厂"""

    def __init__(self):
        self.query_optimizer = QueryOptimizer()
        self.engine_registry: Dict[DatabaseType, Type[BaseStreamingEngine]] = {
            DatabaseType.MYSQL: MySQLStreamingEngine,
            DatabaseType.CLICKHOUSE: ClickHouseStreamingEngine,
        }
        self.performance_history: Dict[str, EnginePerformance] = {}

        GLOG.DEBUG("StreamingEngineFactory initialized")

    def detect_database_type(self, connection) -> DatabaseType:
        """
        自动检测数据库类型

        Args:
            connection: 数据库连接

        Returns:
            数据库类型
        """
        try:
            # 尝试通过连接属性检测
            if hasattr(connection, "driver_name"):
                driver_name = connection.driver_name.lower()
                if "mysql" in driver_name:
                    return DatabaseType.MYSQL
                elif "clickhouse" in driver_name:
                    return DatabaseType.CLICKHOUSE

            # 尝试通过连接URL检测
            if hasattr(connection, "_get_uri"):
                uri = connection._get_uri().lower()
                if "mysql" in uri:
                    return DatabaseType.MYSQL
                elif "clickhouse" in uri:
                    return DatabaseType.CLICKHOUSE

            # 尝试通过引擎URL检测
            if hasattr(connection, "engine") and hasattr(connection.engine, "url"):
                url_str = str(connection.engine.url).lower()
                if "mysql" in url_str:
                    return DatabaseType.MYSQL
                elif "clickhouse" in url_str:
                    return DatabaseType.CLICKHOUSE

            GLOG.WARNING("Could not detect database type, defaulting to UNKNOWN")
            return DatabaseType.UNKNOWN

        except Exception as e:
            GLOG.WARNING(f"Error detecting database type: {e}")
            return DatabaseType.UNKNOWN

    def create_engine(
        self, connection, config: StreamingConfig, db_type: Optional[DatabaseType] = None
    ) -> BaseStreamingEngine:
        """
        创建适合的流式查询引擎

        Args:
            connection: 数据库连接
            config: 流式查询配置
            db_type: 数据库类型（可选，自动检测）

        Returns:
            流式查询引擎实例

        Raises:
            StreamingEngineError: 引擎创建失败
        """
        try:
            # 自动检测数据库类型
            if db_type is None:
                db_type = self.detect_database_type(connection)

            # 检查引擎是否支持
            if db_type not in self.engine_registry:
                raise StreamingEngineError(f"Unsupported database type: {db_type}")

            # 创建引擎实例
            engine_class = self.engine_registry[db_type]
            engine = engine_class(connection, config)

            GLOG.INFO(f"Created {db_type.value} streaming engine: {engine}")
            return engine

        except Exception as e:
            error_msg = f"Failed to create streaming engine: {e}"
            GLOG.ERROR(error_msg)
            raise StreamingEngineError(error_msg) from e

    def get_optimal_engine(
        self, connection, config: StreamingConfig, query: str, filters: Optional[Dict] = None
    ) -> BaseStreamingEngine:
        """
        获取最优的流式查询引擎（基于查询分析和性能历史）

        Args:
            connection: 数据库连接
            config: 流式查询配置
            query: SQL查询语句
            filters: 查询过滤条件

        Returns:
            最优流式查询引擎实例
        """
        try:
            # 检测数据库类型
            db_type = self.detect_database_type(connection)

            # 分析查询
            analysis = self.query_optimizer.analyze_query(query, filters)

            # 记录查询分析结果
            GLOG.DEBUG(
                f"Query analysis - Complexity: {analysis.complexity_score}, "
                f"Estimated rows: {analysis.estimated_rows}, "
                f"Suggestions: {len(analysis.optimization_suggestions)}"
            )

            # 应用优化建议到配置
            optimized_config = self._apply_optimization_to_config(config, analysis, db_type)

            # 创建引擎
            engine = self.create_engine(connection, optimized_config, db_type)

            # 记录引擎使用
            self._record_engine_usage(engine, analysis)

            return engine

        except Exception as e:
            error_msg = f"Failed to get optimal engine: {e}"
            GLOG.ERROR(error_msg)
            raise StreamingEngineError(error_msg) from e

    def _apply_optimization_to_config(
        self, config: StreamingConfig, analysis: QueryAnalysis, db_type: DatabaseType
    ) -> StreamingConfig:
        """
        根据查询分析结果优化配置

        Args:
            config: 原始配置
            analysis: 查询分析结果
            db_type: 数据库类型

        Returns:
            优化后的配置
        """
        # 创建配置副本
        optimized_config = StreamingConfig(
            enabled=config.enabled,
            performance=config.performance,
            monitoring=config.monitoring,
            recovery=config.recovery,
        )

        # 根据复杂度调整批处理大小
        if analysis.complexity_score > 70:
            # 高复杂度查询，使用较小批次
            optimized_config.performance.default_batch_size = min(config.performance.default_batch_size // 2, 500)
        elif analysis.complexity_score < 30:
            # 低复杂度查询，可以使用较大批次
            optimized_config.performance.default_batch_size = min(
                config.performance.default_batch_size * 2, config.performance.max_batch_size
            )

        # 根据预估行数调整
        if analysis.estimated_rows and analysis.estimated_rows > 1000000:
            # 大数据集，启用内存监控
            optimized_config.monitoring.enable_memory_monitoring = True
            optimized_config.performance.adaptive_batch_size = True

        # 数据库特定优化
        if db_type == DatabaseType.CLICKHOUSE:
            # ClickHouse列式存储优化
            optimized_config.performance.enable_column_optimization = True
            if analysis.has_aggregations:
                optimized_config.performance.enable_shard_awareness = True

        elif db_type == DatabaseType.MYSQL:
            # MySQL行式存储优化
            if analysis.has_joins:
                optimized_config.performance.default_batch_size = min(
                    optimized_config.performance.default_batch_size, 1000
                )

        return optimized_config

    def _record_engine_usage(self, engine: BaseStreamingEngine, analysis: QueryAnalysis):
        """记录引擎使用情况"""
        try:
            engine_type = engine.get_db_type()
            current_time = time.time()

            # 更新性能历史
            if engine_type not in self.performance_history:
                self.performance_history[engine_type] = EnginePerformance(
                    engine_type=engine_type,
                    avg_query_time=0.0,
                    success_rate=1.0,
                    memory_efficiency=1.0,
                    throughput_rate=0.0,
                    last_updated=current_time,
                )

            GLOG.DEBUG(f"Recorded usage for {engine_type} engine")

        except Exception as e:
            GLOG.WARNING(f"Failed to record engine usage: {e}")

    def get_performance_stats(self) -> Dict[str, EnginePerformance]:
        """获取引擎性能统计"""
        return self.performance_history.copy()

    def analyze_query_only(self, query: str, filters: Optional[Dict] = None) -> QueryAnalysis:
        """
        仅分析查询，不创建引擎

        Args:
            query: SQL查询语句
            filters: 查询过滤条件

        Returns:
            查询分析结果
        """
        return self.query_optimizer.analyze_query(query, filters)

    def register_custom_engine(self, db_type: DatabaseType, engine_class: Type[BaseStreamingEngine]):
        """
        注册自定义引擎

        Args:
            db_type: 数据库类型
            engine_class: 引擎类
        """
        self.engine_registry[db_type] = engine_class
        GLOG.INFO(f"Registered custom engine for {db_type.value}: {engine_class.__name__}")

    def get_supported_databases(self) -> List[DatabaseType]:
        """获取支持的数据库类型列表"""
        return list(self.engine_registry.keys())

    def __repr__(self) -> str:
        return (
            f"StreamingEngineFactory("
            f"supported_dbs={[db.value for db in self.get_supported_databases()]}, "
            f"performance_records={len(self.performance_history)})"
        )


# 全局工厂实例
streaming_engine_factory = StreamingEngineFactory()
