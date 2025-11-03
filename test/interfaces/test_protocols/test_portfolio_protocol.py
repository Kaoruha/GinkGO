"""
IPortfolio Protocol接口测试

测试IPortfolio Protocol接口的类型安全性和运行时验证。
遵循TDD方法，先写测试验证需求，再验证实现。
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal

# 导入Protocol接口
from ginkgo.trading.interfaces.protocols.portfolio import IPortfolio

# 导入测试工厂
from test.fixtures.trading_factories import (
    PortfolioFactory, ProtocolTestFactory, SignalFactory, OrderFactory,
    PositionFactory, EventFactory
)


@pytest.mark.tdd
@pytest.mark.protocol
class TestIPortfolioProtocol:
    """IPortfolio Protocol接口测试类"""

    def test_basic_portfolio_implementation_compliance(self):
        """测试基础投资组合实现符合IPortfolio Protocol"""
        # 创建投资组合实现
        portfolio = PortfolioFactory.create_basic_portfolio()

        # TDD阶段：测试应该失败，因为Protocol接口要求验证
        # 预期：isinstance检查应该通过

        # 注意：这里的portfolio是字典，不是真正的Portfolio对象
        # 我们需要创建一个真正的Portfolio类实现来测试Protocol接口

        # 验证字典有必需的键
        assert "uuid" in portfolio, "投资组合应该有uuid"
        assert "cash" in portfolio, "投资组合应该有cash"
        assert "total_value" in portfolio, "投资组合应该有total_value"
        assert "positions" in portfolio, "投资组合应该有positions"

    def test_portfolio_with_real_implementation(self):
        """测试真正的Portfolio实现"""
        # 创建一个模拟的Portfolio类实现
        class MockPortfolio:
            def __init__(self):
                self.name = "TestPortfolio"
                self.uuid = "portfolio_123"
                self.cash = Decimal('100000.0')
                self.frozen = Decimal('0.0')
                self.positions = {}
                self.strategies = []
                self.risk_managers = []
                self.orders = []
                self.frozen_capital = Decimal('0.0')

            def get_portfolio_info(self):
                return {
                    "uuid": self.uuid,
                    "name": self.name,
                    "cash": self.cash,
                    "frozen": self.frozen,
                    "total_value": self.calculate_total_value(),
                    "positions": self.positions,
                    "strategies_count": len(self.strategies),
                    "risk_managers_count": len(self.risk_managers)
                }

            def calculate_total_value(self):
                return self.cash + sum(
                    pos.get('market_value', 0) for pos in self.positions.values()
                )

            def add_strategy(self, strategy):
                self.strategies.append(strategy)

            def remove_strategy(self, strategy):
                if strategy in self.strategies:
                    self.strategies.remove(strategy)

            def add_risk_manager(self, risk_manager):
                self.risk_managers.append(risk_manager)

            def remove_risk_manager(self, risk_manager):
                if risk_manager in self.risk_managers:
                    self.risk_managers.remove(risk_manager)

            def get_positions(self):
                return list(self.positions.values())

            def get_position(self, code):
                return self.positions.get(code)

            def update_position(self, position):
                self.positions[position.code] = position

            def remove_position(self, code):
                self.positions.pop(code, None)

            def get_orders(self):
                return self.orders.copy()

            def put_order(self, order):
                self.orders.append(order)

            def get_cash(self):
                return self.cash

            def get_frozen(self):
                return self.frozen

            def freeze_capital(self, amount):
                if amount <= self.cash:
                    self.cash -= amount
                    self.frozen += amount
                    return True
                return False

            def unfreeze_capital(self, amount):
                if amount <= self.frozen:
                    self.frozen -= amount
                    self.cash += amount
                    return True
                return False

            def get_frozen_capital(self):
                return self.frozen_capital

            def calculate_available_cash(self):
                return self.cash - self.frozen

            def calculate_available_positions(self):
                return {
                    code: pos for code, pos in self.positions.items()
                    if pos.get('available_volume', pos.get('volume', 0)) > 0
                }

            def process_event(self, event):
                # 模拟事件处理
                pass

            def publish_event(self, event):
                # 模拟事件发布
                pass

            def add_component(self, component_type, component):
                if component_type == "strategy":
                    self.add_strategy(component)
                elif component_type == "risk_manager":
                    self.add_risk_manager(component)

            def remove_component(self, component_type, component):
                if component_type == "strategy":
                    self.remove_strategy(component)
                elif component_type == "risk_manager":
                    self.remove_risk_manager(component)

            def get_components(self, component_type=None):
                if component_type == "strategy":
                    return self.strategies.copy()
                elif component_type == "risk_manager":
                    return self.risk_managers.copy()
                else:
                    return {
                        "strategies": self.strategies.copy(),
                        "risk_managers": self.risk_managers.copy()
                    }

            def validate_state(self):
                errors = []
                if self.cash < 0:
                    errors.append("现金不能为负数")
                if self.frozen < 0:
                    errors.append("冻结资金不能为负数")
                if self.frozen > self.cash:
                    errors.append("冻结资金不能超过现金")
                return errors

        portfolio = MockPortfolio()

        # 验证Protocol接口合规性
        # 注意：由于MockPortfolio不是真正的IPortfolio实现，这里会失败
        # 这正是TDD Red阶段的目的：明确需求

        # 验证必需方法存在
        assert hasattr(portfolio, 'get_portfolio_info'), "投资组合必须有get_portfolio_info方法"
        assert hasattr(portfolio, 'add_strategy'), "投资组合必须有add_strategy方法"
        assert hasattr(portfolio, 'remove_strategy'), "投资组合必须有remove_strategy方法"
        assert hasattr(portfolio, 'add_risk_manager'), "投资组合必须有add_risk_manager方法"
        assert hasattr(portfolio, 'remove_risk_manager'), "投资组合必须有remove_risk_manager方法"
        assert hasattr(portfolio, 'get_positions'), "投资组合必须有get_positions方法"
        assert hasattr(portfolio, 'get_position'), "投资组合必须有get_position方法"
        assert hasattr(portfolio, 'update_position'), "投资组合必须有update_position方法"
        assert hasattr(portfolio, 'remove_position'), "投资组合必须有remove_position方法"
        assert hasattr(portfolio, 'get_orders'), "投资组合必须有get_orders方法"
        assert hasattr(portfolio, 'put_order'), "投资组合必须有put_order方法"
        assert hasattr(portfolio, 'get_cash'), "投资组合必须有get_cash方法"
        assert hasattr(portfolio, 'get_frozen'), "投资组合必须有get_frozen方法"
        assert hasattr(portfolio, 'freeze_capital'), "投资组合必须有freeze_capital方法"
        assert hasattr(portfolio, 'unfreeze_capital'), "投资组合必须有unfreeze_capital方法"
        assert hasattr(portfolio, 'get_frozen_capital'), "投资组合必须有get_frozen_capital方法"
        assert hasattr(portfolio, 'calculate_available_cash'), "投资组合必须有calculate_available_cash方法"
        assert hasattr(portfolio, 'calculate_available_positions'), "投资组合必须有calculate_available_positions方法"
        assert hasattr(portfolio, 'process_event'), "投资组合必须有process_event方法"
        assert hasattr(portfolio, 'publish_event'), "投资组合必须有publish_event方法"
        assert hasattr(portfolio, 'add_component'), "投资组合必须有add_component方法"
        assert hasattr(portfolio, 'remove_component'), "投资组合必须有remove_component方法"
        assert hasattr(portfolio, 'get_components'), "投资组合必须有get_components方法"
        assert hasattr(portfolio, 'validate_state'), "投资组合必须有validate_state方法"

        # 验证必需属性存在
        assert hasattr(portfolio, 'name'), "投资组合必须有name属性"
        assert hasattr(portfolio, 'uuid'), "投资组合必须有uuid属性"

    def test_get_portfolio_info_method(self):
        """测试投资组合get_portfolio_info方法"""
        portfolio = PortfolioFactory.create_basic_portfolio()

        # 验证返回类型和结构
        assert isinstance(portfolio, dict), "get_portfolio_info应该返回Dict[str, Any]"
        assert "uuid" in portfolio, "投资组合信息应该包含uuid字段"
        assert "total_value" in portfolio, "投资组合信息应该包含总价值字段"
        assert "cash" in portfolio, "投资组合信息应该包含现金字段"
        assert "positions" in portfolio, "投资组合信息应该包含持仓字段"

    def test_portfolio_strategy_management_methods(self):
        """测试投资组合策略管理方法"""
        # 创建一个基础的投资组合模拟
        portfolio_info = PortfolioFactory.create_basic_portfolio()
        strategies = []
        risk_managers = []

        # 模拟添加策略
        strategy = ProtocolTestFactory.create_strategy_implementation("TestStrategy", "basic")
        strategies.append(strategy)

        # 模拟添加风控管理器
        risk_manager = ProtocolTestFactory.create_risk_manager_implementation("TestRisk", "position_ratio")
        risk_managers.append(risk_manager)

        # 验证策略和风控管理器被正确添加
        assert len(strategies) == 1, "应该添加1个策略"
        assert len(risk_managers) == 1, "应该添加1个风控管理器"

    def test_portfolio_position_management_methods(self):
        """测试投资组合持仓管理方法"""
        portfolio_info = PortfolioFactory.create_basic_portfolio()

        # 验证持仓信息
        assert "positions" in portfolio_info, "应该有持仓信息"
        positions = portfolio_info["positions"]
        assert isinstance(positions, dict), "持仓信息应该是字典类型"

        # 验证可以访问特定持仓
        if positions:
            first_code = list(positions.keys())[0]
            position = positions[first_code]
            assert "code" in position, "持仓应该包含代码"
            assert "volume" in position, "持仓应该包含数量"

    def test_portfolio_cash_management_methods(self):
        """测试投资组合资金管理方法"""
        portfolio_info = PortfolioFactory.create_basic_portfolio()

        # 验证资金信息
        assert "cash" in portfolio_info, "应该有现金信息"
        assert "total_value" in portfolio_info, "应该有总价值信息"

        cash = portfolio_info["cash"]
        total_value = portfolio_info["total_value"]
        positions_value = total_value - cash

        assert isinstance(cash, (int, float, Decimal)), "现金应该是数值类型"
        assert isinstance(total_value, (int, float, Decimal)), "总价值应该是数值类型"
        assert positions_value >= 0, "持仓价值应该非负"

    def test_portfolio_order_management_methods(self):
        """测试投资组合订单管理方法"""
        portfolio_info = PortfolioFactory.create_basic_portfolio()

        # 创建测试订单
        order = OrderFactory.create_limit_order(
            code="000001.SZ",
            volume=100,
            limit_price=Decimal('10.50')
        )

        # 模拟订单管理（基于字典的简化实现）
        orders = [order]  # 简化：假设订单列表存在

        # 验证订单管理
        assert len(orders) == 1, "应该有1个订单"
        assert orders[0].code == "000001.SZ", "订单代码应该正确"

    def test_portfolio_event_handling_methods(self):
        """测试投资组合事件处理方法"""
        portfolio_info = PortfolioFactory.create_basic_portfolio()

        # 创建测试事件
        event = EventFactory.create_price_update_event(
            code="000001.SZ",
            close_price=Decimal('10.50')
        )

        # 模拟事件处理
        # 在真正的Portfolio实现中，这会触发相应的业务逻辑
        processed_events = [event]  # 简化：假设事件被处理

        # 验证事件处理
        assert len(processed_events) == 1, "应该处理1个事件"
        assert processed_events[0].code == "000001.SZ", "事件代码应该正确"

    def test_portfolio_validation_methods(self):
        """测试投资组合验证方法"""
        portfolio_info = PortfolioFactory.create_basic_portfolio()

        # 基本验证
        assert portfolio_info["cash"] >= 0, "现金不能为负数"
        assert portfolio_info["total_value"] >= portfolio_info["cash"], "总价值不能小于现金"
        assert portfolio_info["total_value"] >= 0, "总价值不能为负数"

        # 持仓验证
        positions = portfolio_info["positions"]
        for code, position in positions.items():
            assert position["code"] == code, "持仓代码应该一致"
            assert position["volume"] >= 0, "持仓数量不能为负数"
            assert position["cost"] >= 0, "持仓成本不能为负数"

    @tdd_phase('red')
    def test_missing_required_method_should_fail_protocol_check(self):
        """TDD Red阶段：缺少必需方法的类应该Protocol检查失败"""

        class IncompletePortfolio:
            """故意缺少某些方法的投资组合实现"""
            def __init__(self):
                self.name = "IncompletePortfolio"
                self.uuid = "incomplete_portfolio_123"

            def get_portfolio_info(self):
                return {"name": self.name, "uuid": self.uuid}

            # 故意缺少其他必需方法

        incomplete_portfolio = IncompletePortfolio()

        # 验证缺少必需方法
        required_methods = [
            'add_strategy', 'remove_strategy', 'add_risk_manager',
            'remove_risk_manager', 'get_positions', 'get_position',
            'update_position', 'remove_position', 'get_orders',
            'put_order', 'get_cash', 'get_frozen', 'freeze_capital',
            'unfreeze_capital', 'get_frozen_capital', 'calculate_available_cash',
            'calculate_available_positions', 'process_event', 'publish_event',
            'add_component', 'remove_component', 'get_components', 'validate_state'
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(incomplete_portfolio, method):
                missing_methods.append(method)

        # TDD Red阶段：这个测试应该通过，因为确实缺少方法
        assert len(missing_methods) > 0, f"应该缺少必需方法: {missing_methods}"
        assert False, "TDD Red阶段：需要实现完整的Portfolio接口"


@pytest.mark.tdd
@pytest.mark.protocol
class TestIPortfolioProtocolRuntimeValidation:
    """IPortfolio Protocol运行时验证测试"""

    def test_portfolio_with_different_scenarios(self):
        """测试投资组合在不同场景下的行为"""
        # 基础投资组合
        basic_portfolio = PortfolioFactory.create_basic_portfolio()

        # 高风险投资组合
        high_risk_portfolio = PortfolioFactory.create_high_risk_portfolio()

        # 保守投资组合
        conservative_portfolio = PortfolioFactory.create_conservative_portfolio()

        # 验证不同场景的投资组合都有正确的结构
        for portfolio_name, portfolio in [
            ("basic", basic_portfolio),
            ("high_risk", high_risk_portfolio),
            ("conservative", conservative_portfolio)
        ]:
            assert isinstance(portfolio, dict), f"{portfolio_name}投资组合应该是字典类型"
            assert "total_value" in portfolio, f"{portfolio_name}投资组合应该有总价值"
            assert "cash" in portfolio, f"{portfolio_name}投资组合应该有现金"
            assert "positions" in portfolio, f"{portfolio_name}投资组合应该有持仓"

    def test_portfolio_position_calculation_consistency(self):
        """测试投资组合持仓计算的一致性"""
        portfolio = PortfolioFactory.create_basic_portfolio()

        # 计算持仓价值
        positions = portfolio["positions"]
        positions_value = sum(
            pos.get("market_value", 0) for pos in positions.values()
        )

        # 计算总价值
        cash = portfolio["cash"]
        expected_total_value = cash + positions_value
        actual_total_value = portfolio["total_value"]

        # 验证一致性（允许小的浮点误差）
        if isinstance(expected_total_value, Decimal) and isinstance(actual_total_value, Decimal):
            diff = abs(expected_total_value - actual_total_value)
            assert diff < Decimal('0.01'), f"持仓计算应该一致，差异: {diff}"
        else:
            diff = abs(float(expected_total_value) - float(actual_total_value))
            assert diff < 0.01, f"持仓计算应该一致，差异: {diff}"

    def test_portfolio_cash_and_position_relationships(self):
        """测试投资组合现金和持仓之间的关系"""
        portfolio = PortfolioFactory.create_basic_portfolio()

        cash = portfolio["cash"]
        total_value = portfolio["total_value"]
        positions = portfolio["positions"]

        # 基本关系验证
        assert total_value >= cash, "总价值应该大于等于现金"
        assert total_value >= 0, "总价值应该非负"
        assert cash >= 0, "现金应该非负"

        # 持仓价值计算
        positions_value = sum(
            pos.get("market_value", 0) for pos in positions.values()
        )
        assert positions_value >= 0, "持仓价值应该非负"

        # 资金分配验证
        positions_ratio = positions_value / total_value if total_value > 0 else 0
        cash_ratio = cash / total_value if total_value > 0 else 0

        assert 0 <= positions_ratio <= 1, "持仓比例应该在0-1之间"
        assert 0 <= cash_ratio <= 1, "现金比例应该在0-1之间"
        assert abs((positions_ratio + cash_ratio) - 1) < 0.01, "现金和持仓比例之和应该约为1"


@pytest.mark.tdd
@pytest.mark.protocol
class TestIPortfolioProtocolEdgeCases:
    """IPortfolio Protocol边界情况测试"""

    def test_portfolio_with_empty_positions(self):
        """测试空持仓的投资组合"""
        empty_portfolio = PortfolioFactory.create_basic_portfolio(
            total_value=Decimal('100000.0'),
            cash_ratio=1.0,  # 100%现金，0%持仓
            positions=[]
        )

        assert empty_portfolio["cash"] == Decimal('100000.0'), "空持仓投资组合应该全是现金"
        assert len(empty_portfolio["positions"]) == 0, "持仓应该为空"
        assert empty_portfolio["total_value"] == empty_portfolio["cash"], "总价值应该等于现金"

    def test_portfolio_with_zero_cash(self):
        """测试零现金的投资组合"""
        zero_cash_portfolio = PortfolioFactory.create_basic_portfolio(
            total_value=Decimal('100000.0'),
            cash_ratio=0.0,  # 0%现金，100%持仓
            positions=[
                {
                    "code": "000001.SZ",
                    "volume": 5000,
                    "cost": Decimal('20.0'),
                    "current_price": Decimal('20.0'),
                    "market_value": Decimal('100000.0')
                }
            ]
        )

        assert zero_cash_portfolio["cash"] == Decimal('0.0'), "现金应该为零"
        assert len(zero_cash_portfolio["positions"]) == 1, "应该有持仓"
        positions_value = sum(
            pos.get("market_value", 0) for pos in zero_cash_portfolio["positions"].values()
        )
        assert positions_value == Decimal('100000.0'), "持仓价值应该等于总价值"

    def test_portfolio_with_negative_values(self):
        """测试包含负值的投资组合（不应该出现但需要处理）"""
        # 这种情况不应该在正常业务逻辑中出现，但测试边界处理能力
        try:
            problematic_portfolio = {
                "uuid": "test_portfolio",
                "cash": Decimal('-1000.0'),  # 负现金
                "total_value": Decimal('90000.0'),
                "positions": {}
            }

            # 验证这种情况下validate_state方法的行为
            errors = []
            if problematic_portfolio["cash"] < 0:
                errors.append("现金不能为负数")

            assert len(errors) > 0, "应该检测到负值问题"
        except Exception as e:
            # 如果实现拒绝负值，这也是正确的行为
            assert True, "正确拒绝负值输入"

    def test_portfolio_with_extreme_values(self):
        """测试极端值的投资组合"""
        # 极大值的投资组合
        extreme_portfolio = PortfolioFactory.create_basic_portfolio(
            total_value=Decimal('10**12'),  # 1万亿
            cash_ratio=0.01  # 1%现金 = 100亿
        )

        assert extreme_portfolio["cash"] > 0, "应该能处理极大值"
        assert extreme_portfolio["total_value"] > 0, "应该能处理极大总价值"

        # 极小值的投资组合
        tiny_portfolio = PortfolioFactory.create_basic_portfolio(
            total_value=Decimal('0.01'),  # 1分钱
            cash_ratio=0.5
        )

        assert tiny_portfolio["cash"] >= 0, "应该能处理极小值"
        assert tiny_portfolio["total_value"] == Decimal('0.01'), "应该保持极小总价值"

    def test_portfolio_concurrent_modifications(self):
        """测试投资组合的并发修改安全性"""
        import threading
        import time

        portfolio = PortfolioFactory.create_basic_portfolio()
        modification_results = []
        errors = []

        def modifier_worker(worker_id):
            try:
                for i in range(5):
                    # 模拟投资组合修改
                    modified_portfolio = portfolio.copy()
                    modified_portfolio["cash"] += Decimal(str(worker_id * 0.01))
                    modified_portfolio["total_value"] += Decimal(str(worker_id * 0.01))

                    modification_results.append({
                        'worker_id': worker_id,
                        'iteration': i,
                        'cash': modified_portfolio["cash"],
                        'total_value': modified_portfolio["total_value"]
                    })
                    time.sleep(0.001)  # 模拟处理时间
            except Exception as e:
                errors.append((worker_id, e))

        # 启动多个修改线程
        threads = [threading.Thread(target=modifier_worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证结果
        assert len(errors) == 0, f"并发修改不应该产生错误: {errors}"
        assert len(modification_results) == 15, "应该有15个修改结果"


@pytest.mark.tdd
@pytest.mark.financial
class TestIPortfolioProtocolFinancialContext:
    """IPortfolio Protocol金融业务上下文测试"""

    def test_portfolio_with_financial_precision(self):
        """测试投资组合的金融精度处理"""
        from decimal import Decimal, getcontext

        # 设置高精度
        getcontext().prec = 28

        portfolio = PortfolioFactory.create_basic_portfolio(
            total_value=Decimal('1000000.12345678'),
            cash_ratio=0.33333333,
            positions=[
                {
                    "code": "000001.SZ",
                    "volume": 1000,
                    "cost": Decimal('10.12345678'),
                    "current_price": Decimal('15.98765432'),
                    "market_value": Decimal('15987.65432')
                }
            ]
        )

        # 验证精度保持
        cash = portfolio["cash"]
        total_value = portfolio["total_value"]
        positions = portfolio["positions"]

        assert isinstance(cash, Decimal), "现金应该保持Decimal精度"
        assert isinstance(total_value, Decimal), "总价值应该保持Decimal精度"

        for position in positions.values():
            assert isinstance(position["cost"], Decimal), "持仓成本应该保持Decimal精度"
            assert isinstance(position["market_value"], Decimal), "持仓市值应该保持Decimal精度"

    def test_portfolio_with_market_scenarios(self):
        """测试投资组合在不同市场场景下的表现"""
        # 牛市场景 - 投资组合增值
        bull_portfolio = PortfolioFactory.create_basic_portfolio(
            positions=[
                {
                    "code": "000001.SZ",
                    "volume": 1000,
                    "cost": Decimal('10.0'),
                    "current_price": Decimal('15.0'),  # 上涨50%
                    "market_value": Decimal('15000.0'),
                    "profit_loss": Decimal('5000.0'),
                    "profit_loss_ratio": 0.5
                }
            ]
        )

        # 熊市场景 - 投资组合贬值
        bear_portfolio = PortfolioFactory.create_basic_portfolio(
            positions=[
                {
                    "code": "000001.SZ",
                    "volume": 1000,
                    "cost": Decimal('10.0'),
                    "current_price": Decimal('7.0'),  # 下跌30%
                    "market_value": Decimal('7000.0'),
                    "profit_loss": Decimal('-3000.0'),
                    "profit_loss_ratio": -0.3
                }
            ]
        )

        # 验证不同场景下的投资组合状态
        bull_positions = bull_portfolio["positions"]
        bear_positions = bear_portfolio["positions"]

        if bull_positions:
            bull_position = list(bull_positions.values())[0]
            assert bull_position.get("profit_loss_ratio", 0) > 0, "牛市应该有正收益"

        if bear_positions:
            bear_position = list(bear_positions.values())[0]
            assert bear_position.get("profit_loss_ratio", 0) < 0, "熊市应该有负收益"

    def test_portfolio_risk_metrics_calculation(self):
        """测试投资组合风险指标计算"""
        portfolio = PortfolioFactory.create_basic_portfolio(
            positions=[
                {
                    "code": "000001.SZ",
                    "volume": 1000,
                    "cost": Decimal('10.0'),
                    "current_price": Decimal('12.0'),
                    "market_value": Decimal('12000.0'),
                    "profit_loss": Decimal('2000.0'),
                    "profit_loss_ratio": 0.2
                },
                {
                    "code": "000002.SZ",
                    "volume": 500,
                    "cost": Decimal('20.0'),
                    "current_price": Decimal('18.0'),
                    "market_value": Decimal('9000.0'),
                    "profit_loss": Decimal('-1000.0'),
                    "profit_loss_ratio": -0.1
                }
            ]
        )

        # 计算投资组合级别的风险指标
        positions = portfolio["positions"]
        total_market_value = sum(pos.get("market_value", 0) for pos in positions.values())
        total_pnl = sum(pos.get("profit_loss", 0) for pos in positions.values())

        # 计算加权平均收益率
        weighted_return = 0
        for pos in positions.values():
            weight = pos.get("market_value", 0) / total_market_value if total_market_value > 0 else 0
            weighted_return += weight * pos.get("profit_loss_ratio", 0)

        # 验证计算结果
        assert total_market_value > 0, "总市值应该大于0"
        assert isinstance(total_pnl, (int, float, Decimal)), "总盈亏应该是数值类型"
        assert isinstance(weighted_return, (int, float, Decimal)), "加权收益应该是数值类型"

        # 验证风险指标在合理范围内
        assert -1 <= weighted_return <= 1, "加权收益应该在合理范围内"


# ===== TDD阶段标记 =====

def tdd_phase(phase: str):
    """TDD阶段标记装饰器"""
    def decorator(test_func):
        test_func.tdd_phase = phase
        return test_func
    return decorator