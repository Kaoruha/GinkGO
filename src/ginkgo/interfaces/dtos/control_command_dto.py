# Upstream: LiveDataCore.TaskTimer (定时任务调度器)
# Downstream: LiveDataCore.DataManager, ExecutionNode (控制命令处理)
# Role: 控制命令数据传输对象

from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class ControlCommandDTO(BaseModel):
    """
    控制命令数据传输对象

    TaskTimer发送控制命令到Kafka，
    DataManager和ExecutionNode接收并执行对应操作。
    """

    # 命令标识
    command: str = Field(..., description="命令类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="命令时间戳")

    # 命令参数
    params: Dict[str, Any] = Field(default_factory=dict, description="命令参数")

    # 来源标识
    source: Optional[str] = Field(default="task_timer", description="命令来源")
    correlation_id: Optional[str] = Field(None, description="关联ID（用于追踪）")

    # 预定义命令类型
    class Commands:
        """预定义命令常量"""
        BAR_SNAPSHOT = "bar_snapshot"  # K线快照：触发当日K线分析
        UPDATE_SELECTOR = "update_selector"  # 更新选择器：触发Selector重新选股
        UPDATE_DATA = "update_data"  # 更新数据：触发外部数据源更新

    def is_bar_snapshot(self) -> bool:
        """是否为K线快照命令"""
        return self.command == self.Commands.BAR_SNAPSHOT

    def is_update_selector(self) -> bool:
        """是否为更新选择器命令"""
        return self.command == self.Commands.UPDATE_SELECTOR

    def is_update_data(self) -> bool:
        """是否为更新数据命令"""
        return self.command == self.Commands.UPDATE_DATA

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
