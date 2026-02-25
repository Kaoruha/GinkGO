# T044: LogService 日志查询服务实现
# 封装 Loki LogQL API，提供业务日志查询功能

from typing import List, Dict, Optional
from datetime import datetime


class LogService:
    """日志查询服务 - 封装 Loki LogQL API

    提供业务日志查询功能，支持按组合、策略、链路追踪 ID 等条件过滤。

    Attributes:
        loki_client: Loki HTTP 客户端实例
    """

    # T044: 初始化 LogService
    def __init__(self, loki_client):
        """初始化 LogService

        Args:
            loki_client: Loki HTTP 客户端实例
        """
        self.loki_client = loki_client

    # T044: 查询日志（支持多条件过滤）
    def query_logs(
        self,
        portfolio_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """查询日志

        Args:
            portfolio_id: 组合 ID 过滤
            strategy_id: 策略 ID 过滤
            trace_id: 链路追踪 ID 过滤
            level: 日志级别过滤 (error, warning, info, debug)
            start_time: 开始时间（预留，暂未实现）
            end_time: 结束时间（预留，暂未实现）
            limit: 最大返回结果数
            offset: 偏移量（预留，暂未实现）

        Returns:
            日志条目列表
        """
        logql = self._build_logql(
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            trace_id=trace_id,
            level=level
        )
        return self.loki_client.query(logql, limit)

    # T045: 按组合 ID 查询日志
    def query_by_portfolio(
        self,
        portfolio_id: str,
        level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """按组合 ID 查询日志

        Args:
            portfolio_id: 组合 ID
            level: 日志级别过滤
            limit: 最大返回结果数
            offset: 偏移量（预留）

        Returns:
            日志条目列表
        """
        return self.query_logs(portfolio_id=portfolio_id, level=level, limit=limit)

    # T046: 按追踪 ID 查询完整链路日志
    def query_by_trace_id(self, trace_id: str) -> List[Dict]:
        """按追踪 ID 查询完整链路日志

        Args:
            trace_id: 链路追踪 ID

        Returns:
            该链路的所有日志条目
        """
        return self.query_logs(trace_id=trace_id)

    # T047: 查询错误日志
    def query_errors(
        self,
        portfolio_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """查询错误日志

        Args:
            portfolio_id: 组合 ID 过滤（可选）
            limit: 最大返回结果数

        Returns:
            错误日志条目列表
        """
        return self.query_logs(portfolio_id=portfolio_id, level="error", limit=limit)

    # T048: 获取日志数量统计
    def get_log_count(
        self,
        portfolio_id: Optional[str] = None,
        level: Optional[str] = None
    ) -> int:
        """获取日志数量统计

        Args:
            portfolio_id: 组合 ID 过滤
            level: 日志级别过滤

        Returns:
            日志数量
        """
        logs = self.query_logs(portfolio_id=portfolio_id, level=level, limit=1000)
        return len(logs)

    def _build_logql(self, **filters) -> str:
        """构建 LogQL 查询字符串

        Args:
            **filters: 过滤条件

        Returns:
            LogQL 查询字符串
        """
        return self.loki_client.build_logql(**filters)
