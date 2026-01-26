# Upstream: TradeGatewayAdapter (成交反馈)
# Downstream: ExecutionNode (成交事件消费)
# Role: 订单成交反馈数据传输对象

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class OrderFeedbackDTO(BaseModel):
    """
    订单成交反馈数据传输对象

    TradeGatewayAdapter通过Kafka发送成交事件到ExecutionNode，
    用于更新订单状态和持仓。
    """

    # 订单标识
    order_id: str = Field(..., description="订单ID")
    portfolio_id: str = Field(..., description="投资组合ID")
    engine_id: str = Field(..., description="引擎ID")
    run_id: str = Field(..., description="运行ID")
    code: str = Field(..., description="股票代码")
    direction: str = Field(..., description="交易方向")
    filled_quantity: float = Field(..., description="成交数量")
    fill_price: float = Field(..., description="成交价格")
    timestamp: str = Field(..., description="成交时间戳（ISO格式）")

    # 来源标识
    source: Optional[str] = Field(default="trade_gateway", description="反馈来源")
