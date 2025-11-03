"""
流式查询引擎模块

提供多数据库的流式查询引擎实现，支持MySQL、ClickHouse等数据库的
高性能流式查询处理。

主要组件：
- BaseStreamingEngine: 抽象引擎基类
- MySQLStreamingEngine: MySQL专用流式引擎
- ClickHouseStreamingEngine: ClickHouse专用流式引擎
- EngineFactory: 引擎工厂，自动选择合适的引擎
"""

from ginkgo.data.streaming.engines.base_streaming_engine import BaseStreamingEngine, StreamingCursor, ProgressObserver, CursorType, StreamingMetrics
from ginkgo.data.streaming.engines.mysql_streaming_engine import MySQLStreamingEngine
from ginkgo.data.streaming.engines.clickhouse_streaming_engine import ClickHouseStreamingEngine
from ginkgo.data.streaming.engines.engine_factory import (
    StreamingEngineFactory,
    QueryOptimizer,
    QueryAnalysis,
    DatabaseType,
    EnginePerformance,
    streaming_engine_factory,
)

__all__ = [
    "BaseStreamingEngine",
    "StreamingCursor",
    "ProgressObserver",
    "CursorType",
    "StreamingMetrics",
    "MySQLStreamingEngine",
    "ClickHouseStreamingEngine",
    "StreamingEngineFactory",
    "QueryOptimizer",
    "QueryAnalysis",
    "DatabaseType",
    "EnginePerformance",
    "streaming_engine_factory",
]
