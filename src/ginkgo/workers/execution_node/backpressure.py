# Upstream: ExecutionNode（监控队列状态）
# Downstream: 告警系统（发送背压告警）
# Role: BackpressureChecker监控队列使用率并触发告警


"""
BackpressureChecker - 背压监控器

BackpressureChecker监控PortfolioProcessor的队列使用率，防止内存溢出：

核心功能：
- 监控队列使用率（current_size / max_size）
- 70%使用率：发送WARNING警告
- 95%使用率：丢弃消息并发送CRITICAL告警
- 提供背压统计信息

背压策略：
- WARNING级别（70%）：记录日志，监控系统
- CRITICAL级别（95%）：拒绝新消息，防止内存溢出

使用场景：
- ExecutionNode定期检查所有Portfolio的队列状态
- 检测到高背压时触发告警
- 辅助调优队列大小和处理速度
"""

from typing import Dict, List
from datetime import datetime
from threading import Lock


class BackpressureChecker:
    """背压监控器"""

    def __init__(self, warning_threshold: float = 0.7, critical_threshold: float = 0.95):
        """
        初始化BackpressureChecker

        Args:
            warning_threshold: 警告阈值（默认70%）
            critical_threshold: 严重阈值（默认95%）
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

        # 背压统计
        self.warning_count = 0  # 警告次数
        self.critical_count = 0  # 严重次数
        self.total_checks = 0  # 总检查次数

        # 背压历史记录（最近100次）
        self.backpressure_history: List[Dict] = []
        self.history_max_size = 100

        # 锁保护
        self.lock = Lock()

    def check_queue_status(self, portfolio_id: str, current_size: int, max_size: int) -> Dict:
        """
        检查队列状态并返回决策

        Args:
            portfolio_id: Portfolio ID
            current_size: 当前队列大小
            max_size: 队列最大大小

        Returns:
            Dict: 背压检查结果
            {
                "portfolio_id": str,
                "usage": float,  # 使用率 (0.0-1.0)
                "level": str,  # "OK", "WARNING", "CRITICAL"
                "action": str,  # "accept", "warn", "reject"
                "message": str
            }
        """
        self.total_checks += 1

        # 计算队列使用率
        if max_size <= 0:
            usage = 0.0
        else:
            usage = current_size / max_size

        # 判断背压级别
        if usage >= self.critical_threshold:
            # CRITICAL级别：拒绝新消息
            level = "CRITICAL"
            action = "reject"
            message = f"Queue {portfolio_id} at {usage*100:.1f}% capacity (CRITICAL)"
            self.critical_count += 1

        elif usage >= self.warning_threshold:
            # WARNING级别：记录警告
            level = "WARNING"
            action = "warn"
            message = f"Queue {portfolio_id} at {usage*100:.1f}% capacity (WARNING)"
            self.warning_count += 1

        else:
            # OK级别：正常
            level = "OK"
            action = "accept"
            message = f"Queue {portfolio_id} at {usage*100:.1f}% capacity"

        # 记录历史
        with self.lock:
            self.backpressure_history.append({
                "timestamp": datetime.now().isoformat(),
                "portfolio_id": portfolio_id,
                "usage": usage,
                "level": level,
                "action": action
            })

            # 限制历史记录大小
            if len(self.backpressure_history) > self.history_max_size:
                self.backpressure_history.pop(0)

        return {
            "portfolio_id": portfolio_id,
            "usage": usage,
            "level": level,
            "action": action,
            "message": message
        }

    def check_all_portfolios(self, portfolios: Dict) -> List[Dict]:
        """
        检查所有Portfolio的队列状态

        Args:
            portfolios: {portfolio_id: PortfolioProcessor}

        Returns:
            List[Dict]: 所有Portfolio的背压状态列表
        """
        results = []

        for portfolio_id, processor in portfolios.items():
            try:
                current_size = processor.input_queue.qsize()
                max_size = processor.max_queue_size

                result = self.check_queue_status(portfolio_id, current_size, max_size)
                results.append(result)

            except Exception as e:
                # 获取队列状态失败
                results.append({
                    "portfolio_id": portfolio_id,
                    "usage": -1,
                    "level": "ERROR",
                    "action": "unknown",
                    "message": f"Failed to check queue status: {e}"
                })

        return results

    def get_statistics(self) -> Dict:
        """
        获取背压统计信息

        Returns:
            Dict: 背压统计数据
        """
        with self.lock:
            return {
                "warning_threshold": self.warning_threshold,
                "critical_threshold": self.critical_threshold,
                "warning_count": self.warning_count,
                "critical_count": self.critical_count,
                "total_checks": self.total_checks,
                "warning_rate": self.warning_count / max(self.total_checks, 1),
                "critical_rate": self.critical_count / max(self.total_checks, 1),
                "history_size": len(self.backpressure_history)
            }

    def get_history(self, limit: int = 10) -> List[Dict]:
        """
        获取最近的背压历史记录

        Args:
            limit: 返回记录数量（默认10条）

        Returns:
            List[Dict]: 最近的背压记录
        """
        with self.lock:
            return self.backpressure_history[-limit:]

    def reset_statistics(self):
        """重置统计计数器"""
        with self.lock:
            self.warning_count = 0
            self.critical_count = 0
            self.total_checks = 0
            self.backpressure_history.clear()

    def __repr__(self) -> str:
        """字符串表示"""
        return (f"BackpressureChecker(warning={self.warning_threshold*100:.0f}%, "
                f"critical={self.critical_threshold*100:.0f}%, "
                f"warnings={self.warning_count}, criticals={self.critical_count})")
