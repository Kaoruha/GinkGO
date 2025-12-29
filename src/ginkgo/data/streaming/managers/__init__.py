# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: Managers管理器模块提供管理器组件的公共接口和导出支持管理器访问支持交易系统功能支持交易系统功能和组件集成提供完整业务支持






"""
流式查询管理器模块

提供流式查询的各种管理功能，包括断点续传、进度跟踪、
内存监控、会话管理等核心管理组件。

主要组件：
- CheckpointManager: 断点续传管理器
- ProgressTracker: 进度跟踪器
- MemoryMonitor: 内存监控器
- SessionManager: 会话管理器
"""

__all__ = []
