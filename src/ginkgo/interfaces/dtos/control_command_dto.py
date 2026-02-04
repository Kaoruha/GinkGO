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

    命令参数说明 (params):
        - BAR_SNAPSHOT:
            - code: 股票代码（必需）
            - full: 是否全量同步，默认 False
            - force: 是否强制更新，默认 False
        - TICK:
            - code: 股票代码（必需）
            - full: 是否全量回填（回溯到上市日），默认 False
              - False: 增量更新（sync_smart，只同步最近7天缺失数据）
              - True: 全量回填（从上市日开始逐日检查）
            - overwrite: 是否强制覆盖已有数据，默认 False
              - False: 跳过已有数据，只获取缺失数据
              - True: 删除已有数据后重新获取（数据修复场景）
            - 组合说明:
              - full=False, overwrite=False: 日常增量更新（推荐）
              - full=True, overwrite=False: 全量补全缺失数据
              - full=True, overwrite=True: 数据修复（全量覆盖）
        - STOCKINFO: 无参数（同步所有股票）
        - ADJUSTFACTOR:
            - code: 股票代码（必需）
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
        BAR_SNAPSHOT = "bar_snapshot"  # K线快照：K线数据采集
        STOCKINFO = "stockinfo"  # 股票信息：同步股票基础信息
        ADJUSTFACTOR = "adjustfactor"  # 复权因子：同步并计算复权因子
        TICK = "tick"  # Tick数据：Tick数据采集
        UPDATE_SELECTOR = "update_selector"  # 更新Selector：触发ExecutionNode的selector.pick()
        UPDATE_DATA = "update_data"  # 更新数据：触发数据更新任务（已弃用）

    def is_bar_snapshot(self) -> bool:
        """是否为K线快照命令"""
        return self.command == self.Commands.BAR_SNAPSHOT

    def is_stockinfo(self) -> bool:
        """是否为股票信息命令"""
        return self.command == self.Commands.STOCKINFO

    def is_adjustfactor(self) -> bool:
        """是否为复权因子命令"""
        return self.command == self.Commands.ADJUSTFACTOR

    def is_tick(self) -> bool:
        """是否为Tick数据命令"""
        return self.command == self.Commands.TICK

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
