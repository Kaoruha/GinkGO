"""
BacktestWorker - 回测任务执行节点

BacktestWorker是回测任务的运行容器，负责：
- 从Kafka接收回测任务分配
- 管理多个BacktestProcessor并发执行
- 上报任务进度和状态到Kafka
- 上报心跳到Redis（供调度器发现）

架构原则（参考ExecutionNode）：
- 云原生无状态设计：状态在内存，重启后清空
- 单向控制流：Scheduler → Kafka → BacktestWorker
- 心跳机制：Redis TTL=30s，10s续约
- 优雅关闭：等待任务完成或超时强制退出
"""

from ginkgo.workers.backtest_worker.node import BacktestWorker
from ginkgo.workers.backtest_worker.task_processor import BacktestProcessor

__all__ = [
    "BacktestWorker",
    "BacktestProcessor",
]
