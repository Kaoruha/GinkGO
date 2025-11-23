"""
风控-投资组合集成测试

替代过度Mock的单元测试，使用真实对象的集成测试：
1. 风控系统与投资组合的真实交互
2. 完整的订单-持仓-风控流程测试
3. 多种风控管理器协同工作测试

设计原则：
- 使用真实对象而非Mock
- 测试完整的业务流程
- 验证组件间正确协作

Author: TDD Framework
Created: 2024-01-15
"""

import pytest
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any

# 测试工具
from test.fixtures.trading_factories import (
    OrderFactory,
    PortfolioFactory,
    EventFactory,
    SignalFactory
)

# 核心导入
try:
    from ginkgo.trading.strategy.risk_managements.position_ratio_risk import PositionRatioRisk
    from ginkgo.trading.strategy.risk_managements.loss_limit_risk import LossLimitRisk
    from ginkgo.trading.strategy.risk_managements.profit_target_risk import ProfitTargetRisk
    from ginkgo.trading.entities.order import Order
    from ginkgo.trading.events.price_update import EventPriceUpdate
    from ginkgo.enums import DIRECTION_TYPES, ORDERSTATUS_TYPES
    GINKGO_AVAILABLE = True
except ImportError:
    GINKGO_AVAILABLE = False


@pytest.mark.integration
class TestRiskPortfolioIntegration:
    """风控-投资组合集成测试"""

    @pytest.fixture
    def multi_risk_managers(self):
        """创建多重风控管理器组合"""
        if not GINKGO_AVAILABLE:
            pytest.skip("Ginkgo modules not available")

        return [
            PositionRatioRisk(max_position_ratio=0.2, max_total_position_ratio=0.8),
            LossLimitRisk(loss_limit=10.0),  # 10%止损
            ProfitTargetRisk(profit_target=0.25)  # 25%止盈
        ]

    def test_complete_order_risk_control_flow(self, multi_risk_managers):
        """测试：完整的订单风控流程"""
        if not GINKGO_AVAILABLE:
            pytest.skip("Ginkgo modules not available")

        # 1. 创建标准投资组合
        portfolio = PortfolioFactory.create_basic_portfolio(
            total_value=Decimal('100000.0'),
            cash_ratio=0.6  # 60%现金，40%持仓
        )

        # 2. 创建大额订单（可能触发仓位风控）
        large_order = OrderFactory.create_limit_order(
            code="000002.SZ",  # 新股票
            volume=2500,
            limit_price=Decimal('12.0')  # 30000元，占总资产30%
        )

        # 3. 依次通过所有风控管理器
        final_order = large_order
        for risk_manager in multi_risk_managers:
            final_order = risk_manager.cal(portfolio, final_order)

        # 4. 验证风控效果
        # 仓位风控应该将订单调整到20%限制内
        max_allowed_value = portfolio["total_value"] * Decimal('0.2')  # 20000
        max_allowed_volume = int(max_allowed_value / large_order.limit_price)

        assert final_order.volume <= max_allowed_volume
        assert final_order.volume > 0  # 确保不是完全拒绝

    def test_risk_signal_generation_integration(self, multi_risk_managers):
        """测试：风控信号生成集成"""
        if not GINKGO_AVAILABLE:
            pytest.skip("Ginkgo modules not available")

        # 1. 创建有风险的投资组合（持仓亏损）
        risky_portfolio = PortfolioFactory.create_basic_portfolio()
        risky_portfolio["positions"]["000001.SZ"]["current_price"] = Decimal('8.5')  # 亏损15%
        risky_portfolio["positions"]["000001.SZ"]["market_value"] = Decimal('8500.0')
        risky_portfolio["positions"]["000001.SZ"]["profit_loss"] = Decimal('-1500.0')
        risky_portfolio["positions"]["000001.SZ"]["profit_loss_ratio"] = -0.15

        # 2. 创建价格下跌事件
        price_drop_event = EventFactory.create_price_drop_event(
            code="000001.SZ",
            drop_ratio=0.05,  # 继续下跌5%
            base_price=Decimal('8.5')
        )

        # 3. 收集所有风控管理器的信号
        all_signals = []
        for risk_manager in multi_risk_managers:
            signals = risk_manager.generate_signals(risky_portfolio, price_drop_event)
            all_signals.extend(signals)

        # 4. 验证风控信号
        assert len(all_signals) > 0, "应该生成风控信号"

        # 找到止损信号
        stop_loss_signals = [s for s in all_signals if "loss" in s.reason.lower()]
        assert len(stop_loss_signals) > 0, "应该生成止损信号"

        # 验证信号内容
        stop_loss_signal = stop_loss_signals[0]
        assert stop_loss_signal.code == "000001.SZ"
        assert stop_loss_signal.direction == DIRECTION_TYPES.SHORT

    def test_profit_taking_integration(self, multi_risk_managers):
        """测试：止盈集成测试"""
        if not GINKGO_AVAILABLE:
            pytest.skip("Ginkgo modules not available")

        # 1. 创建盈利投资组合
        profitable_portfolio = PortfolioFactory.create_basic_portfolio()
        profitable_portfolio["positions"]["000001.SZ"]["current_price"] = Decimal('26.0')  # 盈利30%
        profitable_portfolio["positions"]["000001.SZ"]["market_value"] = Decimal('26000.0')
        profitable_portfolio["positions"]["000001.SZ"]["profit_loss"] = Decimal('6000.0')
        profitable_portfolio["positions"]["000001.SZ"]["profit_loss_ratio"] = 0.30

        # 2. 创建价格上涨事件（触发止盈）
        price_rise_event = EventFactory.create_price_rise_event(
            code="000001.SZ",
            rise_ratio=0.02,
            base_price=Decimal('26.0')
        )

        # 3. 检查止盈风控响应
        profit_risk_manager = multi_risk_managers[2]  # ProfitTargetRisk
        profit_signals = profit_risk_manager.generate_signals(profitable_portfolio, price_rise_event)

        # 4. 验证止盈信号
        assert len(profit_signals) > 0, "应该生成止盈信号"

        profit_signal = profit_signals[0]
        assert profit_signal.direction == DIRECTION_TYPES.SHORT
        assert "profit" in profit_signal.reason.lower()

    def test_position_adjustment_with_existing_holdings(self, multi_risk_managers):
        """测试：现有持仓的调整集成"""
        if not GINKGO_AVAILABLE:
            pytest.skip("Ginkgo modules not available")

        # 1. 创建已有持仓接近限制的投资组合
        portfolio = PortfolioFactory.create_basic_portfolio()
        portfolio["positions"]["000001.SZ"]["market_value"] = Decimal('18000.0')  # 18%持仓

        # 2. 创建增加同一股票持仓的订单
        additional_order = OrderFactory.create_limit_order(
            code="000001.SZ",  # 同一股票
            volume=500,
            limit_price=Decimal('20.0')  # 额外10000元，总共28%，超出20%限制
        )

        # 3. 仓位风控处理
        position_risk_manager = multi_risk_managers[0]  # PositionRatioRisk
        adjusted_order = position_risk_manager.cal(portfolio, additional_order)

        # 4. 验证调整结果
        current_position_value = portfolio["positions"]["000001.SZ"]["market_value"]
        max_total_value = portfolio["total_value"] * Decimal('0.2')  # 20%限制
        max_additional_value = max_total_value - current_position_value
        max_additional_volume = int(max_additional_value / additional_order.limit_price)

        assert adjusted_order.volume <= max_additional_volume
        assert adjusted_order.volume >= 0


@pytest.mark.integration
class TestPortfolioRiskScenarios:
    """投资组合风险场景测试"""

    def test_high_volatility_scenario(self):
        """测试：高波动市场场景"""
        if not GINKGO_AVAILABLE:
            pytest.skip("Ginkgo modules not available")

        # 1. 创建风控管理器
        risk_manager = PositionRatioRisk(max_position_ratio=0.15, max_total_position_ratio=0.75)

        # 2. 创建投资组合
        portfolio = PortfolioFactory.create_basic_portfolio(cash_ratio=0.4)

        # 3. 模拟连续大幅波动
        base_price = Decimal('10.0')
        price_changes = [0.08, -0.12, 0.15, -0.08, 0.10]  # 8%、-12%、15%、-8%、10%

        for i, change in enumerate(price_changes):
            new_price = base_price * (1 + Decimal(str(change)))

            # 创建价格事件
            price_event = EventFactory.create_price_update_event(
                close_price=new_price
            )

            # 更新投资组合价格
            portfolio["positions"]["000001.SZ"]["current_price"] = new_price
            portfolio["positions"]["000001.SZ"]["market_value"] = new_price * 1000

            # 检查风控响应
            signals = risk_manager.generate_signals(portfolio, price_event)

            # 在高波动期间，风控应该保持理性，不过度反应
            if len(signals) > 0:
                print(f"波动第{i+1}天 ({change*100:.0f}%), 生成风控信号: {len(signals)}个")

        # 验证最终状态合理
        final_position_ratio = risk_manager.calculate_position_ratio(portfolio, "000001.SZ")
        assert final_position_ratio <= risk_manager.max_position_ratio

    def test_multi_stock_portfolio_risk_balance(self):
        """测试：多股票投资组合风险平衡"""
        if not GINKGO_AVAILABLE:
            pytest.skip("Ginkgo modules not available")

        # 1. 创建多股票投资组合
        multi_stock_portfolio = {
            "uuid": "multi_stock_portfolio",
            "cash": Decimal('30000.0'),
            "total_value": Decimal('100000.0'),
            "positions": {
                "000001.SZ": {
                    "code": "000001.SZ",
                    "volume": 1000,
                    "cost": Decimal('15.0'),
                    "current_price": Decimal('18.0'),
                    "market_value": Decimal('18000.0')  # 18%
                },
                "000002.SZ": {
                    "code": "000002.SZ",
                    "volume": 800,
                    "cost": Decimal('25.0'),
                    "current_price": Decimal('30.0'),
                    "market_value": Decimal('24000.0')  # 24%
                },
                "000003.SZ": {
                    "code": "000003.SZ",
                    "volume": 1200,
                    "cost": Decimal('20.0'),
                    "current_price": Decimal('22.0'),
                    "market_value": Decimal('26400.0')  # 26.4%，超出20%限制
                }
            }
        }

        # 2. 创建风控管理器
        risk_manager = PositionRatioRisk(max_position_ratio=0.2, max_total_position_ratio=0.8)

        # 3. 创建新的买入订单（应该被限制）
        new_order = OrderFactory.create_limit_order(
            code="000004.SZ",  # 新股票
            volume=1000,
            limit_price=Decimal('15.0')  # 15000元，加上现有68.4%，超出80%总限制
        )

        # 4. 风控处理
        adjusted_order = risk_manager.cal(multi_stock_portfolio, new_order)

        # 5. 验证结果
        current_total_position = Decimal('68400.0')  # 18000+24000+26400
        max_total_position = multi_stock_portfolio["total_value"] * Decimal('0.8')  # 80000
        max_new_position = max_total_position - current_total_position  # 11600

        if max_new_position > 0:
            max_new_volume = int(max_new_position / new_order.limit_price)
            assert adjusted_order.volume <= max_new_volume
        else:
            assert adjusted_order.volume == 0  # 应该被完全拒绝


# ===== 性能测试 =====

@pytest.mark.integration
@pytest.mark.slow
class TestRiskPerformanceIntegration:
    """风控性能集成测试"""

    def test_high_frequency_risk_checks(self):
        """测试：高频风控检查性能"""
        if not GINKGO_AVAILABLE:
            pytest.skip("Ginkgo modules not available")

        import time

        # 创建风控管理器
        risk_manager = PositionRatioRisk()
        portfolio = PortfolioFactory.create_basic_portfolio()

        # 测试大量订单处理
        start_time = time.time()

        for i in range(1000):
            order = OrderFactory.create_limit_order(
                volume=100 + i % 500,  # 变化的订单量
                limit_price=Decimal('10.0') + Decimal(str(i % 10))  # 变化的价格
            )
            risk_manager.cal(portfolio, order)

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证性能要求：1000个订单在1秒内处理完成
        assert processing_time < 1.0, f"风控处理耗时过长: {processing_time:.3f}秒"
        print(f"处理1000个订单耗时: {processing_time:.3f}秒")


# ===== 使用指南 =====
"""
集成测试运行命令：

# 运行所有集成测试
pytest test/integration/risk_portfolio_integration_test.py -m integration -v

# 运行性能测试（标记为slow）
pytest test/integration/risk_portfolio_integration_test.py -m "integration and slow" -v

# 跳过慢测试，只运行快速集成测试
pytest test/integration/risk_portfolio_integration_test.py -m "integration and not slow" -v

集成测试优势：
1. 测试真实的组件交互，发现Mock测试无法发现的问题
2. 验证完整的业务流程，确保端到端功能正确
3. 性能测试结合功能测试，确保系统在真实负载下正常工作
"""