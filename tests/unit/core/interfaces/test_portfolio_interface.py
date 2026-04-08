"""
性能: 271MB RSS, 2.45s, 49 tests [PASS]
组合接口单元测试

测试 BasePortfolio、BaseMultiStrategyPortfolio 接口定义，
验证构造、组件管理、仓位计算、权重归一化、验证逻辑等功能。
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from ginkgo.core.interfaces.portfolio_interface import (
    PortfolioStatus,
    RebalanceFrequency,
    BasePortfolio,
    BaseMultiStrategyPortfolio,
)


# ── 具体实现用于测试抽象类 ──────────────────────────────────────────


class ConcretePortfolio(BasePortfolio):
    """BasePortfolio 的具体实现"""

    def add_strategy(self, strategy, weight=1.0):
        if strategy not in self._strategies:
            self._strategies.append(strategy)
            self._strategy_weights[strategy.name] = weight
            self._normalize_weights()

    def remove_strategy(self, strategy):
        if isinstance(strategy, str):
            self._strategies = [s for s in self._strategies if s.name != strategy]
        else:
            if strategy in self._strategies:
                self._strategies.remove(strategy)
        # 清理权重
        self._strategy_weights = {
            name: w for name, w in self._strategy_weights.items()
            if any(s.name == name for s in self._strategies)
        }
        if self._strategy_weights:
            self._normalize_weights()
        return True

    def calculate_target_positions(self, signals):
        return {}

    def rebalance(self, target_positions):
        return {"rebalanced": True}


class ConcreteMultiStrategyPortfolio(BaseMultiStrategyPortfolio):
    """BaseMultiStrategyPortfolio 的具体实现"""

    def add_strategy(self, strategy, weight=1.0):
        if strategy not in self._strategies:
            self._strategies.append(strategy)
            self._strategy_weights[strategy.name] = weight
            self._normalize_weights()

    def remove_strategy(self, strategy):
        if isinstance(strategy, str):
            self._strategies = [s for s in self._strategies if s.name != strategy]
        else:
            if strategy in self._strategies:
                self._strategies.remove(strategy)
        return True

    def calculate_target_positions(self, signals):
        return {}

    def rebalance(self, target_positions):
        return {"rebalanced": True}

    def allocate_capital(self, allocations):
        self._strategy_allocations = allocations

    def rebalance_strategies(self):
        pass


# ── 枚举测试 ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPortfolioStatus:
    """PortfolioStatus 枚举测试"""

    def test_enum_values(self):
        """验证所有状态值"""
        assert PortfolioStatus.INACTIVE.value == "inactive"
        assert PortfolioStatus.ACTIVE.value == "active"
        assert PortfolioStatus.SUSPENDED.value == "suspended"
        assert PortfolioStatus.CLOSED.value == "closed"


@pytest.mark.unit
class TestRebalanceFrequency:
    """RebalanceFrequency 枚举测试"""

    def test_enum_values(self):
        """验证所有频率值"""
        assert RebalanceFrequency.DAILY.value == "daily"
        assert RebalanceFrequency.WEEKLY.value == "weekly"
        assert RebalanceFrequency.MONTHLY.value == "monthly"
        assert RebalanceFrequency.QUARTERLY.value == "quarterly"
        assert RebalanceFrequency.ANNUAL.value == "annual"
        assert RebalanceFrequency.CUSTOM.value == "custom"


# ── BasePortfolio 构造测试 ─────────────────────────────────────────────


@pytest.mark.unit
class TestBasePortfolioConstruction:
    """BasePortfolio 构造测试"""

    def test_default_construction(self):
        """默认参数构造"""
        portfolio = ConcretePortfolio()
        assert portfolio.name == "UnknownPortfolio"
        assert portfolio.initial_capital == 1000000.0
        assert portfolio.status == PortfolioStatus.INACTIVE

    def test_custom_name_and_capital(self):
        """自定义名称和初始资金"""
        portfolio = ConcretePortfolio(name="MyPortfolio", initial_capital=500000.0)
        assert portfolio.name == "MyPortfolio"
        assert portfolio.initial_capital == 500000.0

    def test_initial_component_lists_empty(self):
        """初始组件列表为空"""
        portfolio = ConcretePortfolio()
        assert portfolio.strategies == []
        assert portfolio.analyzers == []
        assert portfolio.sizers == []
        assert portfolio.selectors == []
        assert portfolio.risk_managementss == []

    def test_initial_cash_equals_capital(self):
        """初始现金等于初始资金"""
        portfolio = ConcretePortfolio(initial_capital=500000.0)
        assert portfolio.current_cash == 500000.0

    def test_initial_positions_empty(self):
        """初始持仓为空"""
        portfolio = ConcretePortfolio()
        assert portfolio.positions == {}

    def test_total_value_equals_cash_initially(self):
        """初始总价值等于现金"""
        portfolio = ConcretePortfolio(initial_capital=500000.0)
        assert portfolio.total_value == 500000.0


# ── BasePortfolio 组件管理测试 ─────────────────────────────────────────


@pytest.mark.unit
class TestBasePortfolioComponentManagement:
    """BasePortfolio 组件管理测试"""

    def test_add_analyzer(self):
        """添加分析器"""
        portfolio = ConcretePortfolio()
        analyzer = MagicMock()
        portfolio.add_analyzer(analyzer)
        assert analyzer in portfolio.analyzers

    def test_add_analyzer_no_duplicate(self):
        """不重复添加分析器"""
        portfolio = ConcretePortfolio()
        analyzer = MagicMock()
        portfolio.add_analyzer(analyzer)
        portfolio.add_analyzer(analyzer)
        assert len(portfolio.analyzers) == 1

    def test_add_sizer(self):
        """添加仓位调整器"""
        portfolio = ConcretePortfolio()
        sizer = MagicMock()
        portfolio.add_sizer(sizer)
        assert sizer in portfolio.sizers

    def test_add_selector(self):
        """添加选择器"""
        portfolio = ConcretePortfolio()
        selector = MagicMock()
        portfolio.add_selector(selector)
        assert selector in portfolio.selectors

    def test_add_risk_management(self):
        """添加风险管理器"""
        portfolio = ConcretePortfolio()
        risk = MagicMock()
        portfolio.add_risk_managements(risk)
        assert risk in portfolio.risk_managementss


# ── BasePortfolio 策略权重测试 ─────────────────────────────────────────


@pytest.mark.unit
class TestBasePortfolioWeights:
    """BasePortfolio 策略权重测试"""

    def test_set_strategy_weight(self):
        """设置策略权重"""
        portfolio = ConcretePortfolio()
        portfolio.set_strategy_weight("strategy_a", 0.7)
        portfolio.set_strategy_weight("strategy_b", 0.3)
        # 归一化后总和应为 1.0
        total = sum(portfolio.strategy_weights.values())
        assert abs(total - 1.0) < 1e-6

    def test_get_strategy_weight(self):
        """获取策略权重"""
        portfolio = ConcretePortfolio()
        portfolio.set_strategy_weight("strategy_a", 1.0)
        weight = portfolio.get_strategy_weight("strategy_a")
        assert abs(weight - 1.0) < 1e-6

    def test_get_strategy_weight_default(self):
        """获取不存在策略的权重返回 0.0"""
        portfolio = ConcretePortfolio()
        assert portfolio.get_strategy_weight("nonexistent") == 0.0


# ── BasePortfolio 仓位管理测试 ─────────────────────────────────────────


@pytest.mark.unit
class TestBasePortfolioPositionManagement:
    """BasePortfolio 仓位管理测试"""

    def test_update_position_buy(self):
        """买入更新仓位"""
        portfolio = ConcretePortfolio(initial_capital=100000.0)
        portfolio.update_position("000001.SZ", 1000, 10.0)
        pos = portfolio.get_position("000001.SZ")
        assert pos["quantity"] == 1000
        assert pos["avg_price"] == 10.0
        assert pos["market_value"] == 10000.0
        assert pos["unrealized_pnl"] == 0.0

    def test_update_position_decreases_cash(self):
        """买入减少现金"""
        portfolio = ConcretePortfolio(initial_capital=100000.0)
        portfolio.update_position("000001.SZ", 1000, 10.0)
        assert portfolio.current_cash == 90000.0

    def test_update_position_multiple_buys(self):
        """多次买入计算平均价"""
        portfolio = ConcretePortfolio(initial_capital=100000.0)
        portfolio.update_position("000001.SZ", 1000, 10.0)
        portfolio.update_position("000001.SZ", 1000, 20.0)
        pos = portfolio.get_position("000001.SZ")
        assert pos["quantity"] == 2000
        assert pos["avg_price"] == 15.0

    def test_update_position_sell(self):
        """卖出更新仓位"""
        portfolio = ConcretePortfolio(initial_capital=100000.0)
        portfolio.update_position("000001.SZ", 1000, 10.0)
        portfolio.update_position("000001.SZ", -500, 12.0)
        pos = portfolio.get_position("000001.SZ")
        assert pos["quantity"] == 500
        # 卖出时平均价不变
        assert pos["avg_price"] == 10.0

    def test_update_position_close(self):
        """清仓"""
        portfolio = ConcretePortfolio(initial_capital=100000.0)
        portfolio.update_position("000001.SZ", 1000, 10.0)
        portfolio.update_position("000001.SZ", -1000, 15.0)
        pos = portfolio.get_position("000001.SZ")
        assert pos["quantity"] == 0
        assert pos["market_value"] == 0.0

    def test_get_position_nonexistent(self):
        """获取不存在的持仓"""
        portfolio = ConcretePortfolio()
        pos = portfolio.get_position("nonexistent")
        assert pos["quantity"] == 0
        assert pos["avg_price"] == 0

    def test_get_position_weight(self):
        """获取持仓权重"""
        portfolio = ConcretePortfolio(initial_capital=100000.0)
        portfolio.update_position("000001.SZ", 1000, 10.0)
        weight = portfolio.get_position_weight("000001.SZ")
        expected = 10000.0 / 100000.0
        assert abs(weight - expected) < 1e-6

    def test_get_position_weight_zero_total(self):
        """总价值为零时权重为零"""
        portfolio = ConcretePortfolio(initial_capital=0.0)
        portfolio._cash = 0.0
        weight = portfolio.get_position_weight("000001.SZ")
        assert weight == 0.0


# ── BasePortfolio 配置和验证测试 ───────────────────────────────────────


@pytest.mark.unit
class TestBasePortfolioConfig:
    """BasePortfolio 配置和验证测试"""

    def test_set_rebalance_frequency(self):
        """设置再平衡频率"""
        portfolio = ConcretePortfolio()
        portfolio.set_rebalance_frequency(RebalanceFrequency.WEEKLY)
        assert portfolio._rebalance_frequency == RebalanceFrequency.WEEKLY

    def test_set_position_limits(self):
        """设置仓位限制"""
        portfolio = ConcretePortfolio()
        portfolio.set_position_limits(0.2, 0.1)
        assert portfolio._max_position_size == 0.2
        assert portfolio._cash_reserve == 0.1

    def test_set_position_limits_cash_reserve_none(self):
        """不设置现金保留"""
        portfolio = ConcretePortfolio()
        original_reserve = portfolio._cash_reserve
        portfolio.set_position_limits(0.2)
        assert portfolio._cash_reserve == original_reserve

    def test_validate_empty_strategies(self):
        """无策略验证失败"""
        portfolio = ConcretePortfolio()
        errors = portfolio.validate_portfolio()
        assert any("至少一个策略" in e for e in errors)

    def test_validate_zero_capital(self):
        """零资金验证失败"""
        portfolio = ConcretePortfolio(initial_capital=0)
        errors = portfolio.validate_portfolio()
        assert any("大于0" in e for e in errors)

    def test_validate_invalid_position_size(self):
        """无效仓位比例验证失败"""
        portfolio = ConcretePortfolio()
        portfolio._max_position_size = 1.5
        errors = portfolio.validate_portfolio()
        assert any("仓位比例" in e for e in errors)

    def test_validate_invalid_cash_reserve(self):
        """无效现金保留验证失败"""
        portfolio = ConcretePortfolio()
        portfolio._cash_reserve = -0.1
        errors = portfolio.validate_portfolio()
        assert any("现金保留" in e for e in errors)

    def test_validate_weight_not_sum_to_one(self):
        """策略权重不为 1.0 验证失败"""
        portfolio = ConcretePortfolio()
        portfolio._strategy_weights = {"a": 0.3, "b": 0.3}
        errors = portfolio.validate_portfolio()
        assert any("权重总和" in e for e in errors)

    def test_validate_valid_portfolio(self):
        """有效组合验证通过"""
        portfolio = ConcretePortfolio()
        strategy = MagicMock()
        strategy.name = "test"
        portfolio.add_strategy(strategy)
        errors = portfolio.validate_portfolio()
        # 策略存在、资金有效，不应有策略和资金相关错误
        assert not any("策略" in e or "资金" in e or "大于0" in e for e in errors)


# ── BasePortfolio 生命周期测试 ─────────────────────────────────────────


@pytest.mark.unit
class TestBasePortfolioLifecycle:
    """BasePortfolio 生命周期测试"""

    def test_activate_success(self):
        """成功激活组合"""
        portfolio = ConcretePortfolio()
        strategy = MagicMock()
        strategy.name = "test"
        portfolio.add_strategy(strategy)
        portfolio.activate()
        assert portfolio.status == PortfolioStatus.ACTIVE

    def test_activate_with_errors_raises(self):
        """验证失败激活抛出异常"""
        portfolio = ConcretePortfolio()
        with pytest.raises(ValueError, match="验证失败"):
            portfolio.activate()

    def test_suspend(self):
        """暂停组合"""
        portfolio = ConcretePortfolio()
        strategy = MagicMock()
        strategy.name = "test"
        portfolio.add_strategy(strategy)
        portfolio.activate()
        portfolio.suspend()
        assert portfolio.status == PortfolioStatus.SUSPENDED

    def test_close(self):
        """关闭组合"""
        portfolio = ConcretePortfolio()
        portfolio.close()
        assert portfolio.status == PortfolioStatus.CLOSED

    def test_reset(self):
        """重置组合"""
        portfolio = ConcretePortfolio(initial_capital=100000.0)
        portfolio.update_position("000001.SZ", 1000, 10.0)
        portfolio.reset()
        assert portfolio.status == PortfolioStatus.INACTIVE
        assert portfolio.current_cash == 100000.0
        assert portfolio.positions == {}


# ── BasePortfolio 性能和概要测试 ───────────────────────────────────────


@pytest.mark.unit
class TestBasePortfolioPerformance:
    """BasePortfolio 性能指标测试"""

    def test_calculate_performance_metrics_empty(self):
        """空组合性能指标"""
        portfolio = ConcretePortfolio(initial_capital=100000.0)
        metrics = portfolio.calculate_performance_metrics()
        assert metrics["total_return"] == 0.0
        assert metrics["total_pnl"] == 0.0
        assert metrics["position_count"] == 0

    def test_calculate_performance_metrics_with_positions(self):
        """有持仓时的性能指标"""
        portfolio = ConcretePortfolio(initial_capital=100000.0)
        portfolio.update_position("000001.SZ", 1000, 10.0)
        # 模拟价格变化后更新
        portfolio._positions["000001.SZ"]["market_value"] = 11000.0
        portfolio._positions["000001.SZ"]["unrealized_pnl"] = 1000.0
        metrics = portfolio.calculate_performance_metrics()
        assert metrics["total_pnl"] == 1000.0
        assert abs(metrics["total_return"] - 0.01) < 1e-6

    def test_portfolio_summary_structure(self):
        """组合概要结构"""
        portfolio = ConcretePortfolio(name="TestPortfolio")
        summary = portfolio.get_portfolio_summary()
        assert summary["name"] == "TestPortfolio"
        assert "status" in summary
        assert "initial_capital" in summary
        assert "current_value" in summary
        assert "current_cash" in summary
        assert "strategy_count" in summary
        assert "position_count" in summary
        assert "created_at" in summary

    def test_str_representation(self):
        """字符串表示"""
        portfolio = ConcretePortfolio(name="TestPortfolio")
        s = str(portfolio)
        assert "TestPortfolio" in s


# ── BaseMultiStrategyPortfolio 测试 ────────────────────────────────────


@pytest.mark.unit
class TestBaseMultiStrategyPortfolio:
    """多策略组合接口测试"""

    def test_default_construction(self):
        """默认构造"""
        portfolio = ConcreteMultiStrategyPortfolio()
        assert portfolio.strategy_allocations == {}
        assert portfolio.strategy_performance == {}

    def test_allocate_capital(self):
        """分配资金"""
        portfolio = ConcreteMultiStrategyPortfolio()
        portfolio.allocate_capital({"strategy_a": 500000.0, "strategy_b": 500000.0})
        assert portfolio.strategy_allocations["strategy_a"] == 500000.0

    def test_track_strategy_performance(self):
        """跟踪策略表现"""
        portfolio = ConcreteMultiStrategyPortfolio()
        portfolio.track_strategy_performance("strategy_a", {"total_return": 0.15, "sharpe": 1.5})
        perf = portfolio.get_strategy_performance("strategy_a")
        assert perf["total_return"] == 0.15
        assert perf["sharpe"] == 1.5

    def test_get_strategy_performance_nonexistent(self):
        """获取不存在的策略表现"""
        portfolio = ConcreteMultiStrategyPortfolio()
        assert portfolio.get_strategy_performance("nonexistent") == {}

    def test_get_best_performing_strategy_empty(self):
        """无策略表现时返回 None"""
        portfolio = ConcreteMultiStrategyPortfolio()
        assert portfolio.get_best_performing_strategy() is None

    def test_get_best_performing_strategy(self):
        """获取最佳策略"""
        portfolio = ConcreteMultiStrategyPortfolio()
        portfolio.track_strategy_performance("strategy_a", {"total_return": 0.10})
        portfolio.track_strategy_performance("strategy_b", {"total_return": 0.20})
        best = portfolio.get_best_performing_strategy()
        assert best == "strategy_b"

    def test_inherits_from_iportfolio(self):
        """继承 BasePortfolio"""
        assert issubclass(BaseMultiStrategyPortfolio, BasePortfolio)
