# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: Optimizers优化器模块提供优化器组件的公共接口和导出支持优化器使用支持交易系统功能支持相关功能






"""
流式查询优化器模块

提供SQL查询优化、批次大小优化、索引提示优化等
性能优化功能，针对不同数据库进行专门优化。

主要组件：
- QueryOptimizer: SQL查询优化器
- BatchSizeOptimizer: 批次大小动态优化器
- IndexHintOptimizer: 索引提示优化器
"""

__all__ = []
