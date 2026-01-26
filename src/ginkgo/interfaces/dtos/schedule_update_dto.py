# Upstream: Scheduler, CLI (ginkgo scheduler migrate/reload, ginkgo execution pause/resume)
# Downstream: ExecutionNode (调度更新消费和处理)
# Role: 调度更新通知数据传输对象

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ScheduleUpdateDTO(BaseModel):
    """
    调度更新通知数据传输对象

    Scheduler和CLI通过Kafka发送调度更新到ExecutionNode，
    用于通知节点变更（投资组合迁移、重载、节点暂停/恢复等）。
    """

    # 命令标识
    command: str = Field(..., description="命令类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="命令时间戳")

    # 投资组合相关
    portfolio_id: Optional[str] = Field(None, description="投资组合ID")

    # 节点相关
    source_node: Optional[str] = Field(None, description="源节点ID")
    target_node: Optional[str] = Field(None, description="目标节点ID")
    node_id: Optional[str] = Field(None, description="节点ID（用于pause/resume）")

    # 来源标识
    source: Optional[str] = Field(default="scheduler", description="命令来源")
    correlation_id: Optional[str] = Field(None, description="关联ID（用于追踪）")

    # 预定义命令类型
    class Commands:
        """预定义命令常量"""
        PORTFOLIO_MIGRATE = "portfolio.migrate"  # 投资组合迁移
        PORTFOLIO_RELOAD = "portfolio.reload"  # 投资组合重载
        NODE_PAUSE = "node.pause"  # 节点暂停
        NODE_RESUME = "node.resume"  # 节点恢复

    def is_portfolio_migrate(self) -> bool:
        """是否为投资组合迁移命令"""
        return self.command == self.Commands.PORTFOLIO_MIGRATE

    def is_portfolio_reload(self) -> bool:
        """是否为投资组合重载命令"""
        return self.command == self.Commands.PORTFOLIO_RELOAD

    def is_node_pause(self) -> bool:
        """是否为节点暂停命令"""
        return self.command == self.Commands.NODE_PAUSE

    def is_node_resume(self) -> bool:
        """是否为节点恢复命令"""
        return self.command == self.Commands.NODE_RESUME
