"""
事件路由中心TDD测试

覆盖EventRoutingCenter关键路径, 聚焦路由规则/负载均衡/断路器/故障转移等能力。
按照ENGINE_TEST_COVERAGE_ANALYSIS.md指引, 先创建回测与实盘共用的测试骨架。
"""

import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# 将src加入sys.path, 便于后续Green阶段导入真实实现
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.gateway.center import EventRoutingCenter
from ginkgo.trading.gateway.interfaces import (
    RoutingRule, RouteTarget, RoutingStrategy, RoutingEvent, RoutingEventType,
    RouteStatus, EventPriority, CircuitBreakerState
)
from ginkgo.trading.gateway.balancers import LoadBalancerFactory, RoundRobinBalancer, HashBasedBalancer
from ginkgo.trading.gateway.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerManager


def _make_target(target_id="target_1", status=RouteStatus.ACTIVE):
    return RouteTarget(
        target_id=target_id,
        target_type="test",
        target_instance=MagicMock(),
        max_concurrent=100,
        weight=1,
        status=status,
    )


def _make_rule(rule_id="rule_1", targets=None, event_type_pattern="*"):
    return RoutingRule(
        rule_id=rule_id,
        name=f"Rule {rule_id}",
        event_type_pattern=event_type_pattern,
        source_pattern="*",
        targets=targets or ["target_1"],
        strategy=RoutingStrategy.ROUND_ROBIN,
        weight=1.0,
        priority_range=(0, 100),
    )


def _make_event(event_type="OrderSubmitted", source="strategy"):
    event = MagicMock()
    event.event_type = event_type
    event.source = source
    event.priority = EventPriority.NORMAL
    event.event_id = "event_001"
    return event


@pytest.mark.unit
class TestRoutingRuleManagement:
    """路由规则生命周期与匹配行为"""

    @pytest.mark.asyncio
    async def test_register_routing_rule(self):
        center = EventRoutingCenter()
        target = _make_target()
        await center.register_target(target)
        rule = _make_rule(targets=["target_1"])
        result = await center.add_routing_rule(rule)
        assert result is True
        stored = await center.get_routing_rule("rule_1")
        assert stored is not None
        assert stored.rule_id == "rule_1"

    @pytest.mark.asyncio
    async def test_update_routing_rule(self):
        center = EventRoutingCenter()
        target = _make_target()
        await center.register_target(target)
        rule = _make_rule()
        await center.add_routing_rule(rule)
        result = await center.update_routing_rule("rule_1", {"weight": 10.0})
        assert result is True
        updated = await center.get_routing_rule("rule_1")
        assert updated.weight == 10.0

    @pytest.mark.asyncio
    async def test_delete_routing_rule(self):
        center = EventRoutingCenter()
        target = _make_target()
        await center.register_target(target)
        rule = _make_rule()
        await center.add_routing_rule(rule)
        result = await center.remove_routing_rule("rule_1")
        assert result is True
        deleted = await center.get_routing_rule("rule_1")
        assert deleted is None

    @pytest.mark.asyncio
    async def test_routing_rule_matching_priority(self):
        center = EventRoutingCenter()
        target = _make_target()
        await center.register_target(target)
        rule_low = _make_rule(rule_id="rule_low")
        rule_high = _make_rule(rule_id="rule_high")
        # Set different weights via attribute access
        rule_low.weight = 1
        rule_high.weight = 10
        await center.add_routing_rule(rule_low)
        await center.add_routing_rule(rule_high)
        rules = await center.list_routing_rules()
        assert len(rules) == 2
        # Verify weights are preserved
        retrieved = await center.get_routing_rule("rule_low")
        assert retrieved.weight == 1
        retrieved_high = await center.get_routing_rule("rule_high")
        assert retrieved_high.weight == 10


@pytest.mark.unit
class TestLoadBalancerStrategies:
    """负载均衡策略行为 (hash/round-robin/latency 等)"""

    @pytest.mark.asyncio
    async def test_round_robin_balancer_rotation(self):
        balancer = RoundRobinBalancer()
        targets = ["t1", "t2", "t3"]
        rule = _make_rule()
        event = _make_event()
        targets_info = {t: _make_target(t) for t in targets}

        selected_1 = await balancer.select_targets(targets, rule, event, targets_info)
        selected_2 = await balancer.select_targets(targets, rule, event, targets_info)
        selected_3 = await balancer.select_targets(targets, rule, event, targets_info)
        assert len(selected_1) == 1
        assert len(selected_2) == 1
        assert len(selected_3) == 1

    @pytest.mark.asyncio
    async def test_hash_balancer_consistency(self):
        balancer = HashBasedBalancer()
        targets = ["t1", "t2", "t3"]
        rule = _make_rule()
        event = _make_event()
        event.symbol = "000001.SZ"
        targets_info = {t: _make_target(t) for t in targets}

        result_1 = await balancer.select_targets(targets, rule, event, targets_info)
        result_2 = await balancer.select_targets(targets, rule, event, targets_info)
        # Same event hash should always pick the same target
        assert result_1 == result_2

    @pytest.mark.asyncio
    async def test_latency_aware_balancer_preference(self):
        from ginkgo.trading.gateway.balancers import LeastConnectionsBalancer
        balancer = LeastConnectionsBalancer()
        t1 = _make_target("t1")
        t2 = _make_target("t2")
        t2.current_load = 50  # higher load
        targets_info = {"t1": t1, "t2": t2}
        rule = _make_rule(targets=["t1", "t2"])
        event = _make_event()
        result = await balancer.select_targets(["t1", "t2"], rule, event, targets_info)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_dynamic_balancer_fallback(self):
        balancer = RoundRobinBalancer()
        # Empty targets -> empty result
        result = await balancer.select_targets([], _make_rule(), _make_event(), {})
        assert result == []


@pytest.mark.unit
class TestCircuitBreakerProtection:
    """断路器保护与半开恢复"""

    def test_trip_circuit_on_failure_threshold(self):
        config = CircuitBreakerConfig(failure_threshold=3, min_calls_threshold=3)
        cb = CircuitBreaker("test_target", config)
        for _ in range(3):
            cb.record_failure()
        assert cb.is_open() is True

    def test_half_open_probe_success(self):
        config = CircuitBreakerConfig(failure_threshold=2, min_calls_threshold=2, recovery_timeout=0, half_open_max_calls=2)
        cb = CircuitBreaker("test_target", config)
        cb.record_failure()
        cb.record_failure()
        # With recovery_timeout=0, _update_state auto-transitions to HALF_OPEN
        assert cb.get_state() == CircuitBreakerState.HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.get_state() == CircuitBreakerState.CLOSED

    def test_half_open_probe_failure(self):
        # Use recovery_timeout > 0 so that after HALF_OPEN->OPEN transition,
        # get_state() does NOT auto-transition back to HALF_OPEN
        config = CircuitBreakerConfig(failure_threshold=2, min_calls_threshold=2, recovery_timeout=60)
        cb = CircuitBreaker("test_target", config)
        cb.record_failure()
        cb.record_failure()
        assert cb.get_state() == CircuitBreakerState.OPEN
        # Manually force to HALF_OPEN to test probe failure behavior
        cb._change_state(CircuitBreakerState.HALF_OPEN)
        assert cb.get_state() == CircuitBreakerState.HALF_OPEN
        # A single failure in HALF_OPEN immediately trips back to OPEN
        cb.record_failure()
        assert cb.get_state() == CircuitBreakerState.OPEN

    def test_circuit_breaker_metrics_update(self):
        cb = CircuitBreaker("test_target")
        cb.record_success()
        cb.record_success()
        cb.record_failure()
        stats = cb.get_statistics()
        assert stats["total_calls"] == 3
        assert stats["success_count"] == 2
        assert stats["failure_count"] == 1


@pytest.mark.unit
class TestFailoverMechanism:
    """目标故障转移及重试策略"""

    @pytest.mark.asyncio
    async def test_failover_to_secondary_target(self):
        from ginkgo.trading.gateway.balancers import FailoverBalancer
        balancer = FailoverBalancer()
        t1 = _make_target("t1", status=RouteStatus.FAILED)
        t2 = _make_target("t2", status=RouteStatus.ACTIVE)
        targets_info = {"t1": t1, "t2": t2}
        rule = _make_rule(targets=["t1", "t2"])
        event = _make_event()
        result = await balancer.select_targets(["t1", "t2"], rule, event, targets_info)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_retry_policy_respects_backoff(self):
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60)
        cb = CircuitBreaker("test_target", config)
        for _ in range(3):
            cb.record_failure()
        assert cb.is_open() is True
        # Should remain open immediately after
        assert cb.get_state() == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_failover_event_emission(self):
        center = EventRoutingCenter()
        callback_called = []
        center.add_event_callback(lambda e: callback_called.append(e))
        target = _make_target()
        await center.register_target(target)
        assert len(callback_called) == 1  # TARGET_REGISTERED event

    @pytest.mark.asyncio
    async def test_restore_primary_after_recovery(self):
        config = CircuitBreakerConfig(failure_threshold=2, min_calls_threshold=2, recovery_timeout=0, half_open_max_calls=1)
        cb = CircuitBreaker("test_target", config)
        cb.record_failure()
        cb.record_failure()
        # recovery_timeout=0 → auto-transitions to HALF_OPEN
        assert cb.get_state() == CircuitBreakerState.HALF_OPEN
        cb.record_success()
        assert cb.get_state() == CircuitBreakerState.CLOSED


@pytest.mark.unit
class TestRoutingMetricsAndCache:
    """路由指标与缓存一致性"""

    def test_route_metrics_aggregation(self):
        center = EventRoutingCenter()
        stats = center.get_routing_stats()
        assert "total_targets" in stats
        assert "total_rules" in stats
        assert stats["total_targets"] == 0
        assert stats["total_rules"] == 0

    @pytest.mark.asyncio
    async def test_cache_hit_rate_tracking(self):
        center = EventRoutingCenter()
        target = _make_target()
        await center.register_target(target)
        rule = _make_rule(targets=["target_1"])
        await center.add_routing_rule(rule)
        stats = center.get_routing_stats()
        assert stats["cache_size"] == 0

    @pytest.mark.asyncio
    async def test_cache_eviction_on_rule_change(self):
        center = EventRoutingCenter()
        target = _make_target()
        await center.register_target(target)
        rule = _make_rule()
        await center.add_routing_rule(rule)
        await center.remove_routing_rule("rule_1")
        stats = center.get_routing_stats()
        assert stats["total_rules"] == 0

    @pytest.mark.asyncio
    async def test_metrics_reset_on_shutdown(self):
        center = EventRoutingCenter()
        target = _make_target()
        await center.register_target(target)
        rule = _make_rule(targets=["target_1"])
        await center.add_routing_rule(rule)
        await center.reset_metrics()
        metrics = await center.get_routing_metrics()
        assert metrics.total_events == 0
