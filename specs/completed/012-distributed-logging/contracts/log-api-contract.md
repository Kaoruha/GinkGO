# GLOG API Contract

**Feature**: 012-distributed-logging (Loki Only)
**Version**: 1.0.0
**Date**: 2026-02-26

## 1. GLOG API (向后兼容)

### 1.1 日志记录方法

```python
class GinkgoLogger:
    """Ginkgo 日志记录器 - 基于 structlog 实现"""

    # ========== 日志记录方法 ==========

    def DEBUG(self, msg: str) -> None:
        """记录 DEBUG 级别日志"""

    def INFO(self, msg: str) -> None:
        """记录 INFO 级别日志"""

    def WARN(self, msg: str) -> None:
        """记录 WARNING 级别日志"""

    def ERROR(self, msg: str) -> None:
        """记录 ERROR 级别日志（含智能流量控制）"""

    def CRITICAL(self, msg: str) -> None:
        """记录 CRITICAL 级别日志"""

    # ========== 日志级别控制 ==========

    def set_level(self, level: str, handler_type: str = 'all') -> None:
        """
        设置日志级别

        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            handler_type: handler 类型 ('all', 'console', 'file')

        Example:
            GLOG.set_level("DEBUG", "console")
        """

    def set_console_level(self, level: str) -> None:
        """设置控制台日志级别"""

    def get_current_levels(self) -> Dict[str, str]:
        """获取当前所有 Handler 的日志级别"""

    # ========== 追踪上下文 ==========

    def set_trace_id(self, trace_id: str) -> contextvars.Token:
        """
        设置当前 trace_id（使用 contextvars）

        Args:
            trace_id: 追踪 ID

        Returns:
            Token 用于恢复 context

        Example:
            token = GLOG.set_trace_id("trace-123")
            GLOG.INFO("Processing")
            GLOG.clear_trace_id(token)
        """

    def get_trace_id(self) -> Optional[str]:
        """获取当前 trace_id"""

    def clear_trace_id(self, token: contextvars.Token) -> None:
        """清除 trace_id，恢复之前的值"""

    def with_trace_id(self, trace_id: str) -> ContextManager:
        """
        临时设置 trace_id 的上下文管理器

        Example:
            with GLOG.with_trace_id("trace-123"):
                GLOG.INFO("Step 1")
                GLOG.INFO("Step 2")
        """

    # ========== 业务上下文 ==========

    def set_log_category(self, category: str) -> None:
        """
        设置日志类别

        Args:
            category: "system" 或 "backtest"

        Example:
            GLOG.set_log_category("backtest")
        """

    def bind_context(self, **kwargs) -> None:
        """
        绑定业务上下文（会自动添加到所有后续日志）

        Args:
            **kwargs: 业务上下文字段
                - strategy_id: UUID
                - portfolio_id: UUID
                - event_type: str
                - symbol: str
                - direction: str
                - 其他自定义字段

        Example:
            GLOG.bind_context(
                strategy_id=strategy.uuid,
                portfolio_id=portfolio.uuid
            )
            GLOG.INFO("Signal generated")  # 自动包含上述字段
        """

    def unbind_context(self, *keys: str) -> None:
        """解绑指定的上下文字段"""

    def clear_context(self) -> None:
        """清除所有业务上下文"""

    # ========== 错误统计 ==========

    def get_error_stats(self) -> Dict[str, Any]:
        """
        获取错误统计信息

        Returns:
            {
                "total_error_patterns": 10,
                "top_error_patterns": [...],
                "total_error_count": 150
            }
        """

    def clear_error_stats(self) -> None:
        """清除错误统计"""
```

### 1.2 使用示例

```python
from ginkgo.libs import GLOG

# 基本使用（完全兼容现有代码）
GLOG.INFO("Engine started")
GLOG.ERROR("Database connection failed")

# 业务日志（回测）
GLOG.set_log_category("backtest")
GLOG.bind_context(
    strategy_id=strategy.uuid,
    portfolio_id=portfolio.uuid
)
GLOG.INFO(f"Signal generated: BUY {symbol}")

# 分布式追踪
with GLOG.with_trace_id("trace-123"):
    GLOG.INFO("Processing request")
```

## 2. 配置 API

### 2.1 GCONF 配置项

```yaml
# ~/.ginkgo/config.yaml

logging:
  # 日志模式: auto / container / local
  mode: auto

  # 日志格式: json / plain
  format: json

  # 日志级别
  level:
    console: INFO
    file: DEBUG

  # 容器模式配置
  container:
    enabled: true
    json_output: true

  # 本地模式配置
  local:
    file_enabled: true
    file_path: "ginkgo.log"

  # 敏感字段脱敏
  mask_fields:
    - password
    - secret
    - token
```

### 2.2 配置访问

```python
from ginkgo.libs import GCONF

mode = GCONF.LOGGING_MODE
format = GCONF.LOGGING_FORMAT
console_level = GCONF.LOGGING_LEVEL_CONSOLE
```

## 3. Loki 查询 API (LogQL)

### 3.1 基础查询

```logql
# 查看所有日志
{}

# 按日志类别过滤
{log_category="backtest"}

# 按级别过滤
{level="error"}

# 按容器过滤
{container_id="docker://abc123"}

# 按 trace_id 过滤
{trace_id="trace-123"}

# 内容搜索
{log_category="system"} |= "database"
```

### 3.2 高级查询

```logql
# 组合查询
{log_category="backtest", level="error"} |= "database"

# 时间范围
{level="error"} [1h]

# 统计
count_over_time({level="error"}[1h])

# 按标签分组
count by (logger_name) ({log_category="system"})

# 正则匹配
{log_category="backtest"} |= "~.*Signal.*"
```

## 4. LogService API (Loki 查询)

### 4.1 服务访问

```python
from ginkgo import services

log_service = services.logging.log_service()
```

### 4.2 查询方法

```python
class LogService:
    """日志查询服务 - 封装 Loki LogQL API"""

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
        """
        查询日志（支持多条件过滤）

        Args:
            portfolio_id: 组合ID过滤
            strategy_id: 策略ID过滤
            trace_id: 追踪ID过滤
            level: 日志级别过滤 (debug/info/warning/error/critical)
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            offset: 分页偏移量

        Returns:
            List[Dict]: 日志条目列表
            [
                {
                    "timestamp": "2026-02-26T10:30:00Z",
                    "level": "info",
                    "message": "Engine started",
                    "portfolio_id": "...",
                    "strategy_id": "...",
                    ...
                }
            ]

        Raises:
            ServiceUnavailable: Loki 不可用时抛出（由调用方处理）
        """

    def query_by_portfolio(
        self,
        portfolio_id: str,
        level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """按组合ID查询日志"""

    def query_by_trace_id(self, trace_id: str) -> List[Dict]:
        """按追踪ID查询完整链路日志"""

    def query_errors(
        self,
        portfolio_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """查询错误日志"""

    def get_log_count(
        self,
        portfolio_id: Optional[str] = None,
        level: Optional[str] = None
    ) -> int:
        """获取日志数量统计"""
```

### 4.3 使用示例

```python
from ginkgo import services

log_service = services.logging.log_service()

# 查询某个回测的所有日志
logs = log_service.query_by_portfolio(
    portfolio_id=str(portfolio.uuid),
    limit=200
)

# 查询某个回测的错误日志
errors = log_service.query_errors(
    portfolio_id=str(portfolio.uuid)
)

# 查询追踪链路
trace_logs = log_service.query_by_trace_id(trace_id="trace-123")

# 复杂查询
logs = log_service.query_logs(
    portfolio_id=str(portfolio.uuid),
    level="error",
    start_time=datetime(2026, 2, 26),
    limit=100
)
```

### 4.4 错误处理

```python
try:
    logs = log_service.query_by_portfolio(portfolio_id="xxx")
except ServiceUnavailable as e:
    # Loki 不可用时的处理
    return {"error": "日志服务暂时不可用，请稍后重试"}
```

## 5. 未来扩展：ClickHouse API

当需要复杂业务查询时，可添加 ClickHouse 支持：

```python
# 未来扩展（暂不实现）
# LogService 将扩展 ClickHouse 写入和查询方法
```
