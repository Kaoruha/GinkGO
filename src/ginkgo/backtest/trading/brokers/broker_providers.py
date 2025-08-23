"""
Broker Providers - 符合Ginkgo DI架构的Broker提供器

使用dependency-injector的providers模式，将Broker集成到
现有的DI容器系统中，保持架构一致性。
"""

from dependency_injector import providers
from .base_broker import BaseBroker
from .sim_broker import SimBroker
from .okx_broker import OKXBroker


def _get_sim_broker_class():
    """Lazy import for SimBroker class."""
    return SimBroker


def _get_okx_broker_class():
    """Lazy import for OKXBroker class."""
    return OKXBroker


def _get_base_broker_class():
    """Lazy import for BaseBroker class."""
    return BaseBroker


# 单个broker providers
sim_broker_provider = providers.Factory(_get_sim_broker_class)
okx_broker_provider = providers.Factory(_get_okx_broker_class)

# Broker工厂聚合器 - 符合Ginkgo的FactoryAggregate模式
broker_providers = {
    'sim': sim_broker_provider,
    'okx': okx_broker_provider,
}

# 使用FactoryAggregate统一管理，符合Ginkgo架构风格
brokers = providers.FactoryAggregate(**broker_providers)