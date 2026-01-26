# Upstream: CLI (ginkgo scheduler pause/resume/status/recalculate/schedule)
# Downstream: Scheduler (命令消费和处理)
# Role: Scheduler控制命令数据传输对象

from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class SchedulerCommandDTO(BaseModel):
    """
    Scheduler控制命令数据传输对象

    CLI通过Kafka发送控制命令到Scheduler，
    用于控制调度器的行为（暂停、恢复、重新计算等）。
    """

    # 命令标识
    command: str = Field(..., description="命令类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="命令时间戳")

    # 命令参数
    params: Dict[str, Any] = Field(default_factory=dict, description="命令参数")

    # 来源标识
    source: Optional[str] = Field(default="cli", description="命令来源")
    correlation_id: Optional[str] = Field(None, description="关联ID（用于追踪）")

    # 预定义命令类型
    class Commands:
        """预定义命令常量"""
        PAUSE = "pause"  # 暂停调度器
        RESUME = "resume"  # 恢复调度器
        STATUS = "status"  # 查询状态
        RECALCULATE = "recalculate"  # 重新计算负载均衡
        SCHEDULE = "schedule"  # 执行调度分配

    def is_pause(self) -> bool:
        """是否为暂停命令"""
        return self.command == self.Commands.PAUSE

    def is_resume(self) -> bool:
        """是否为恢复命令"""
        return self.command == self.Commands.RESUME

    def is_status(self) -> bool:
        """是否为状态查询命令"""
        return self.command == self.Commands.STATUS

    def is_recalculate(self) -> bool:
        """是否为重新计算命令"""
        return self.command == self.Commands.RECALCULATE

    def is_schedule(self) -> bool:
        """是否为调度命令"""
        return self.command == self.Commands.SCHEDULE

    def get_param(self, key: str, default: Any = None) -> Any:
        """
        获取命令参数

        Args:
            key: 参数键
            default: 默认值

        Returns:
            参数值
        """
        return self.params.get(key, default)
