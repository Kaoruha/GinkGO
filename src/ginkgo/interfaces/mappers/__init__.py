# Upstream: Kafka consumers (node.py / trade_gateway_adapter / data_manager / portfolio_processor)
# Downstream: 领域 Event / Entity (EventPriceUpdate / EventOrderPartiallyFilled / Order)
# Role: ADR-025 四边界 Mapper 家族的 Kafka 入站亚型 —— consumer 唯一转换点

from .message_mapper import MessageMapper

__all__ = ["MessageMapper"]
