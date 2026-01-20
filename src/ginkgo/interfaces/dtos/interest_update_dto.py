# Upstream: ExecutionNode.Portfolio (投资组合)
# Downstream: LiveDataCore.DataManager (数据订阅管理)
# Role: 订阅更新数据传输对象

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class InterestUpdateDTO(BaseModel):
    """
    订阅更新数据传输对象

    ExecutionNode的Portfolio通过Selector选出感兴趣的标的后，
    发送InterestUpdateDTO到Kafka，DataManager接收后更新订阅列表。
    """

    portfolio_id: str = Field(..., description="投资组合ID")
    node_id: str = Field(..., description="ExecutionNode节点ID")
    symbols: List[str] = Field(default_factory=list, description="订阅的股票代码列表")
    timestamp: datetime = Field(default_factory=datetime.now, description="更新时间")

    # 订阅类型
    update_type: str = Field(default="replace", description="更新类型：replace(替换)/add(添加)/remove(删除)")

    def get_all_symbols(self) -> set:
        """
        获取所有订阅标的

        Returns:
            标的集合
        """
        return set(self.symbols)

    def is_replace(self) -> bool:
        """是否为替换模式"""
        return self.update_type == "replace"

    def is_add(self) -> bool:
        """是否为添加模式"""
        return self.update_type == "add"

    def is_remove(self) -> bool:
        """是否为删除模式"""
        return self.update_type == "remove"
