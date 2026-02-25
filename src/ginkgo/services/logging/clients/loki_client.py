# T042: Grafana Loki HTTP 客户端实现
# 封装 Loki API 调用，支持日志查询和 LogQL 构建

import requests
from typing import Dict, List, Any, Optional


class LokiClient:
    """Grafana Loki HTTP 客户端

    封装 Loki HTTP API，提供日志查询和 LogQL 构建功能。

    Attributes:
        base_url: Loki API endpoint URL
    """

    def __init__(self, base_url: str = "http://localhost:3100"):
        """初始化 Loki 客户端

        Args:
            base_url: Loki API endpoint URL
        """
        self.base_url = base_url

    # T042: 查询日志（调用 Loki HTTP API）
    def query(self, logql: str, limit: int = 100) -> List[Dict]:
        """查询日志

        Args:
            logql: LogQL 查询字符串
            limit: 最大返回结果数

        Returns:
            日志条目列表，每个条目包含 timestamp 和 message
        """
        try:
            response = requests.get(
                f"{self.base_url}/loki/api/v1/query",
                params={"query": logql, "limit": limit},
                timeout=5
            )
            response.raise_for_status()
            return self._parse_response(response)
        except requests.exceptions.RequestException:
            # T049: Loki 不可用时的错误处理 - 优雅降级
            return []

    def _parse_response(self, response) -> List[Dict]:
        """解析 Loki 响应

        Args:
            response: requests.Response 对象

        Returns:
            解析后的日志条目列表
        """
        data = response.json()
        if "data" not in data:
            return []

        results = data["data"].get("result", [])
        logs = []
        for result in results:
            for entry in result.get("values", []):
                # entry: [timestamp_ns, log_line]
                if len(entry) >= 2:
                    logs.append({"timestamp": entry[0], "message": entry[1]})
        return logs

    # T043: LogQL 查询字符串构建
    def build_logql(self, **filters) -> str:
        """构建 LogQL 查询字符串

        Args:
            **filters: 过滤条件，支持:
                - portfolio_id: 组合 ID
                - strategy_id: 策略 ID
                - trace_id: 链路追踪 ID
                - level: 日志级别

        Returns:
            LogQL 查询字符串
        """
        selectors = []

        if "portfolio_id" in filters:
            selectors.append(f'portfolio_id="{filters["portfolio_id"]}"')
        if "strategy_id" in filters:
            selectors.append(f'strategy_id="{filters["strategy_id"]}"')
        if "trace_id" in filters:
            selectors.append(f'trace_id="{filters["trace_id"]}"')
        if "level" in filters:
            selectors.append(f'level="{filters["level"]}"')

        if selectors:
            return "{" + ", ".join(selectors) + "}"
        return "{}"
