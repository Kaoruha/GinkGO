# Upstream: ExecutionNode (订单提交)
# Downstream: TradeGatewayAdapter (订单消费和执行)
# Role: 订单提交数据传输对象

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class OrderSubmissionDTO(BaseModel):
    """
    订单提交数据传输对象

    ExecutionNode通过Kafka发送订单到TradeGatewayAdapter，
    用于订单执行和反馈。
    """

    # 订单标识
    order_id: str = Field(..., description="订单ID")
    portfolio_id: str = Field(..., description="投资组合ID")
    code: str = Field(..., description="股票代码")
    direction: str = Field(..., description="交易方向")
    volume: float = Field(..., description="交易数量")
    price: Optional[str] = Field(None, description="价格（字符串格式）")
    timestamp: Optional[str] = Field(None, description="时间戳（ISO格式）")

    # 来源标识
    source: Optional[str] = Field(default="execution_node", description="订单来源")
