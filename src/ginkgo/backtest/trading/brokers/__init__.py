"""
Broker模块 - 统一的交易执行接口

该模块提供了统一的Broker接口，支持多种交易执行方式：
- SimBroker: 模拟撮合，用于回测
- OKXBroker: OKX交易所接口
- IBKRBroker: 盈透证券接口（未来扩展）

符合Ginkgo DI架构，通过dependency-injector管理Broker实例。

使用示例:
    from ginkgo import services
    
    # 通过DI容器创建Broker
    sim_broker = services.backtest.brokers.sim(config)
    okx_broker = services.backtest.brokers.okx(config)
"""

from .base_broker import BaseBroker
from .sim_broker import SimBroker
from .okx_broker import OKXBroker
from .broker_providers import brokers, sim_broker_provider, okx_broker_provider

__all__ = [
    "BaseBroker",
    "SimBroker", 
    "OKXBroker",
    "brokers",
    "sim_broker_provider",
    "okx_broker_provider"
]