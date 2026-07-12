"""
gateway 抽象层命名迁移测试（ADR-022 原则 1 + 原则 2 / #6116）

覆盖：
- 原则 1：`I*` 前缀删除（IEventRoutingCenter/ICircuitBreaker/ILoadBalancer 退场）
- 原则 2：单实现 ABC 降级为具体类（EventRoutingCenter/CircuitBreaker 不再是 ABC 派生）
- 多实现纯契约保留为无前缀 ABC（LoadBalancer(ABC) 仍是 BaseLoadBalancer 的基类）
- 行为不变：CircuitBreaker 熔断阈值逻辑未被改名破坏
"""

import importlib
from abc import ABC

import pytest

import ginkgo.trading.gateway as gateway_pkg
from ginkgo.trading.gateway import EventRoutingCenter, CircuitBreaker, LoadBalancer
from ginkgo.trading.gateway.balancers import BaseLoadBalancer


class TestIIprefixRemoved:
    """原则 1：`I*` 前缀从公共 API 退场。"""

    @pytest.mark.parametrize("removed_name", [
        "IEventRoutingCenter",
        "ICircuitBreaker",
        "ILoadBalancer",
    ])
    def test_old_iprefix_names_gone_from_package(self, removed_name):
        # 包级导出不再含 I* 前缀类
        assert not hasattr(gateway_pkg, removed_name), (
            f"{removed_name} 应已从 ginkgo.trading.gateway 退场（ADR-022 原则 1）"
        )
        # __all__ 同步清理
        assert removed_name not in gateway_pkg.__all__

    def test_interfaces_module_no_longer_defines_iprefix(self):
        interfaces = importlib.import_module("ginkgo.trading.gateway.interfaces")
        for removed in ("IEventRoutingCenter", "ICircuitBreaker", "ILoadBalancer"):
            assert not hasattr(interfaces, removed), (
                f"interfaces.{removed} 应已删除/改名"
            )


class TestSingleImplDowngradedToConcrete:
    """原则 2：单实现 ABC 降级为具体类，不再经 ABC 契约派生。"""

    def test_event_routing_center_is_concrete(self):
        # 降级后不再继承 ABC（IEventRoutingCenter(ABC) 已删，EventRoutingCenter 独立）
        assert ABC not in EventRoutingCenter.__mro__, (
            "EventRoutingCenter 应为具体类，不再经 ABC 契约派生（ADR-022 原则 2）"
        )

    def test_circuit_breaker_is_concrete(self):
        assert ABC not in CircuitBreaker.__mro__, (
            "CircuitBreaker 应为具体类，不再经 ABC 契约派生（ADR-022 原则 2）"
        )


class TestMultiImplContractPreserved:
    """多实现纯契约：LoadBalancer 去前缀但保留 ABC。"""

    def test_loadbalancer_is_abstract_contract(self):
        # 多实现族：保留为无前缀 ABC，仍含抽象方法
        assert ABC in LoadBalancer.__mro__
        assert getattr(LoadBalancer, "__abstractmethods__", set()), (
            "LoadBalancer 应保留为纯契约 ABC（多实现族，ADR-022 原则 1）"
        )

    def test_base_loadbalancer_inherits_loadbalancer(self):
        assert issubclass(BaseLoadBalancer, LoadBalancer)

    def test_loadbalancer_factory_still_produces_balancers(self):
        from ginkgo.trading.gateway.balancers import LoadBalancerFactory
        from ginkgo.trading.gateway.interfaces import RoutingStrategy
        balancer = LoadBalancerFactory.create_balancer(RoutingStrategy.ROUND_ROBIN)
        assert isinstance(balancer, LoadBalancer)


class TestCircuitBreakerBehaviorUnchanged:
    """改名/降级未破坏 CircuitBreaker 熔断行为。"""

    def test_opens_after_failure_threshold(self):
        # 默认 failure_threshold=5；连续失败达阈值即开路
        breaker = CircuitBreaker("test-target")
        for _ in range(5):
            breaker.record_failure()
        assert breaker.is_open() is True
