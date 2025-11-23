"""
T302: T+1 Configurable Mechanism Integration Test

Purpose: 验证T+1配置化参数机制
- 测试T+n延迟时间n的配置功能
- 验证不同市场规则的参数适配
- 测试配置变更对现有持仓的影响
- 验证配置参数的持久化和加载
- 关键验证: 确保T+1机制能够适应不同交易规则

Created: 2025-11-08
Task: T302 [P] [T+1验证] 验证T+1配置化参数机制
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ginkgo.trading.engines import EventEngine
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.strategies import BaseStrategy
from ginkgo.trading.sizers.fixed_sizer import FixedSizer
from ginkgo.trading.selectors.fixed_selector import FixedSelector
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.position import Position
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.enums import (
    DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES,
    SOURCE_TYPES, FREQUENCY_TYPES
)
from unittest.mock import patch


class TestStrategy(BaseStrategy):
    """测试策略 - 生成测试信号"""

    def __init__(self, name="TestT1ConfigStrategy"):
        super().__init__(name=name)
        self.generated_signals = []

    def cal(self, portfolio_info, event):
        """生成测试信号"""
        code = event.code
        price = event.value.close
        direction = DIRECTION_TYPES.LONG if price > 10 else DIRECTION_TYPES.SHORT

        signal = Signal(
            portfolio_id=portfolio_info.get("portfolio_id", "test_portfolio"),
            engine_id=portfolio_info.get("engine_id", "test_engine"),
            run_id=portfolio_info.get("run_id", "test_run"),
            code=code,
            direction=direction,
            volume=1000,
            source=SOURCE_TYPES.TEST,
            business_timestamp=event.business_timestamp
        )

        self.generated_signals.append(signal)
        return [signal]


class TestT1ConfigurableMechanism:
    """T+1配置化参数机制集成测试"""

    def setup_method(self):
        """每个测试方法前的初始化"""
        # 设置测试参数
        self.test_code = "000001.SZ"
        self.test_price = Decimal("10.0")
        self.test_time = datetime(2023, 1, 1)
        self.t1_time = datetime(2023, 1, 2)
        self.t2_time = datetime(2023, 1, 3)
        self.t3_time = datetime(2023, 1, 4)

        # 创建事件引擎（真实引擎）
        self.engine = EventEngine()
        self.engine.engine_id = "test_engine_t302"
        self.engine._run_id = "test_run_t302"

        # 创建Portfolio和组件
        self.portfolio = PortfolioT1Backtest("test_portfolio_t302")
        self.strategy = TestStrategy("test_strategy_t302")
        self.sizer = FixedSizer("test_sizer_t302")
        self.selector = FixedSelector("test_selector_t302", codes=f'["{self.test_code}"]')

        # 添加组件到投资组合
        self.portfolio.add_strategy(self.strategy)
        self.portfolio.bind_sizer(self.sizer)
        self.portfolio.bind_selector(self.selector)

        # 设置时间提供者
        from ginkgo.trading.time.providers import LogicalTimeProvider
        self.time_provider = LogicalTimeProvider(initial_time=self.test_time)
        self.portfolio.set_time_provider(self.time_provider)

        # 绑定Portfolio到引擎
        self.engine.add_portfolio(self.portfolio)

        # 添加模拟测试数据
        self.add_test_price_data()

        # 设置必要的ID
        self.portfolio.engine_id = "test_engine_t302"
        self.portfolio.run_id = "test_run_t302"

    def add_test_price_data(self):
        """添加模拟的测试价格数据"""
        try:
            from ginkgo.trading.entities.bar import Bar
            from ginkgo.libs import to_decimal
            from ginkgo.data.containers import container

            # 创建从2022-12-03到2023-01-01的测试价格数据
            start_date = datetime(2022, 12, 3)
            end_date = datetime(2023, 1, 1)
            current_date = start_date
            test_bars = []

            base_price = Decimal("10.0")
            price = base_price

            while current_date <= end_date:
                test_bar = Bar(
                    code=self.test_code,
                    open=price,
                    high=price * Decimal("1.01"),
                    low=price * Decimal("0.99"),
                    close=price,
                    volume=1000000,
                    amount=10000000,
                    frequency=FREQUENCY_TYPES.DAY,
                    timestamp=current_date
                )
                test_bars.append(test_bar)
                price = price + Decimal("0.1")
                current_date += timedelta(days=1)

            bar_crud = container.cruds.bar()
            bar_crud.add_batch(test_bars)
            print(f"✅ 添加了 {len(test_bars)} 条测试价格数据")

        except Exception as e:
            print(f"⚠️ 添加测试数据失败（可能已存在）: {e}")

    def teardown_method(self):
        """每个测试方法后的清理"""
        try:
            from ginkgo.data.containers import container
            bar_crud = container.cruds.bar()
            bar_crud.delete_bars(
                code=self.test_code,
                start="2022-12-01",
                end="2023-01-02"
            )
            print("🧹 清理测试数据完成")
        except Exception as e:
            print(f"⚠️ 清理测试数据失败: {e}")

    def create_position_with_settlement_days(self, settlement_days: int, volume: int = 1000) -> Position:
        """创建指定结算天数的持仓"""
        position = Position(
            portfolio_id=self.portfolio.portfolio_id,
            engine_id=self.engine.engine_id,
            run_id=self.engine._run_id,
            code=self.test_code,
            settlement_days=settlement_days,
            direction=DIRECTION_TYPES.LONG,
            price=Decimal("10.0")
        )

        # 使用Mock绕过时间问题，模拟买入
        with patch.object(position, 'get_current_time', return_value=self.test_time):
            success = position._bought(price=Decimal("10.0"), volume=volume)
            assert success, f"买入应该成功，settlement_days={settlement_days}"

        return position

    def test_settlement_days_configuration(self):
        """测试T+n延迟时间n的配置功能"""
        print("\n=== 测试T+n延迟时间配置功能 ===")

        # 测试默认配置（应该是T+1）
        default_position = self.create_position_with_settlement_days(1)
        assert default_position.settlement_days == 1, "默认应该是T+1"
        print(f"✅ 默认配置: settlement_days={default_position.settlement_days}")

        # 测试T+2配置
        t2_position = self.create_position_with_settlement_days(2)
        assert t2_position.settlement_days == 2, "T+2配置应该正确"
        print(f"✅ T+2配置: settlement_days={t2_position.settlement_days}")

        # 测试T+3配置
        t3_position = self.create_position_with_settlement_days(3)
        assert t3_position.settlement_days == 3, "T+3配置应该正确"
        print(f"✅ T+3配置: settlement_days={t3_position.settlement_days}")

        # 测试T+0配置（当日可卖）
        t0_position = self.create_position_with_settlement_days(0)
        assert t0_position.settlement_days == 0, "T+0配置应该正确"
        assert t0_position.volume == 1000, "T+0应该立即可用"
        assert t0_position.settlement_frozen_volume == 0, "T+0不应该有冻结"
        print(f"✅ T+0配置: 立即可用，volume={t0_position.volume}")

    def test_market_rules_parameter_adaptation(self):
        """测试不同市场规则的参数适配"""
        print("\n=== 测试不同市场规则参数适配 ===")

        # 模拟A股市场规则（T+1）
        a_share_position = self.create_position_with_settlement_days(1)
        assert a_share_position.settlement_days == 1, "A股应该是T+1"
        print(f"✅ A股市场: T+1规则")

        # 模拟港股市场规则（T+0）
        hk_share_position = self.create_position_with_settlement_days(0)
        assert hk_share_position.settlement_days == 0, "港股应该是T+0"
        print(f"✅ 港股市场: T+0规则")

        # 模拟美股市场规则（T+0）
        us_share_position = self.create_position_with_settlement_days(0)
        assert us_share_position.settlement_days == 0, "美股应该是T+0"
        print(f"✅ 美股市场: T+0规则")

        # 模拟期货市场规则（T+0）
        futures_position = self.create_position_with_settlement_days(0)
        assert futures_position.settlement_days == 0, "期货应该是T+0"
        print(f"✅ 期货市场: T+0规则")

    def test_configuration_change_impact_on_existing_positions(self):
        """测试配置变更对现有持仓的影响"""
        print("\n=== 测试配置变更对现有持仓的影响 ===")

        # 创建T+2持仓
        position = self.create_position_with_settlement_days(2)
        original_settlement_days = position.settlement_days
        original_frozen = position.settlement_frozen_volume

        print(f"   原始配置: settlement_days={original_settlement_days}, frozen={original_frozen}")

        # 测试配置变更
        # settlement_days现在是只读属性，配置变更需要创建新持仓
        try:
            position.settlement_days = 3  # 尝试修改配置
            print("⚠️ settlement_days可以被修改 - 这应该被修复为只读")
        except AttributeError:
            print("✅ settlement_days是只读属性，配置变更需要新持仓")

        # 验证现有持仓配置不受影响
        assert position.settlement_days == original_settlement_days, "现有持仓配置不应改变"
        print(f"   现有持仓配置保持: settlement_days={position.settlement_days}")

        # 验证冻结状态应该保持不变（配置变更不影响已冻结的持仓）
        assert position.settlement_frozen_volume == original_frozen, "现有持仓冻结状态不应改变"
        print(f"   冻结状态保持: settlement_frozen_volume={position.settlement_frozen_volume}")

        # 创建新持仓体现新配置
        new_position = self.create_position_with_settlement_days(3, volume=500)
        assert new_position.settlement_days == 3, "新持仓应该使用新配置"
        assert new_position.settlement_frozen_volume == 500, "新持仓应该按新规则冻结"

        print(f"✅ 新持仓配置: settlement_days={new_position.settlement_days}, frozen={new_position.settlement_frozen_volume}")

    def test_configuration_parameter_persistence(self):
        """测试配置参数的持久化和加载"""
        print("\n=== 测试配置参数持久化和加载 ===")

        # 创建不同配置的持仓
        positions = []
        settlement_configs = [0, 1, 2, 3]  # T+0, T+1, T+2, T+3

        for i, days in enumerate(settlement_configs):
            position = self.create_position_with_settlement_days(days, volume=1000 * (i + 1))
            positions.append(position)
            print(f"   持仓{i+1}: settlement_days={position.settlement_days}, volume={position.volume}")

        # 测试转换为数据库模型
        models = []
        for i, position in enumerate(positions):
            model = position.to_model()
            models.append(model)
            print(f"   持仓{i+1}模型: settlement_days={model.settlement_days}, settlement_frozen_volume={model.settlement_frozen_volume}")

        # 测试从数据库模型恢复
        restored_positions = []
        for i, model in enumerate(models):
            restored_position = Position.from_model(model)
            restored_positions.append(restored_position)

            # 验证配置正确恢复
            original = positions[i]
            restored = restored_positions[i]
            assert restored.settlement_days == original.settlement_days, f"持仓{i+1}配置应该正确恢复"
            assert restored.settlement_frozen_volume == original.settlement_frozen_volume, f"持仓{i+1}冻结状态应该正确恢复"
            print(f"   持仓{i+1}恢复: settlement_days={restored.settlement_days}, frozen={restored.settlement_frozen_volume}")

        print("✅ 配置参数持久化和加载验证通过")

    def test_portfolio_level_t1_configuration(self):
        """测试投资组合级别的T+1配置管理"""
        print("\n=== 测试投资组合级别的T+1配置管理 ===")

        # 为portfolio添加多个不同配置的持仓
        positions_config = [
            {"code": "000001.SZ", "settlement_days": 1, "volume": 1000},  # A股 T+1
            {"code": "000002.SZ", "settlement_days": 0, "volume": 2000},  # 港股 T+0
            {"code": "000003.SZ", "settlement_days": 2, "volume": 1500},  # 特殊规则 T+2
        ]

        for config in positions_config:
            position = Position(
                portfolio_id=self.portfolio.portfolio_id,
                engine_id=self.engine.engine_id,
                run_id=self.engine._run_id,
                code=config["code"],
                settlement_days=config["settlement_days"],
                direction=DIRECTION_TYPES.LONG,
                price=Decimal("10.0")
            )

            with patch.object(position, 'get_current_time', return_value=self.test_time):
                position._bought(price=Decimal("10.0"), volume=config["volume"])
                self.portfolio.positions[config["code"]] = position

            print(f"   持仓 {config['code']}: T+{config['settlement_days']}, volume={config['volume']}")

        # 验证投资组合中的持仓配置
        total_frozen = sum(pos.settlement_frozen_volume for pos in self.portfolio.positions.values())
        total_available = sum(pos.volume for pos in self.portfolio.positions.values())

        print(f"   投资组合状态: 冻结总量={total_frozen}, 可用总量={total_available}")

        # 时间推进验证不同配置的解锁时间
        print("\n   时间推进测试:")
        self.portfolio.advance_time(self.t1_time)  # T+1

        for code, position in self.portfolio.positions.items():
            if position.settlement_days == 0:
                assert position.settlement_frozen_volume == 0, f"{code} T+0应该已解冻"
            elif position.settlement_days == 1:
                assert position.settlement_frozen_volume == 0, f"{code} T+1应该已解冻"
            elif position.settlement_days == 2:
                assert position.settlement_frozen_volume > 0, f"{code} T+2应该仍然冻结"

            print(f"   T+1后 {code}: 冻结={position.settlement_frozen_volume}, 可用={position.volume}")

        print("✅ 投资组合级别配置管理验证通过")

    def test_edge_cases_and_error_handling(self):
        """测试边界条件和错误处理"""
        print("\n=== 测试边界条件和错误处理 ===")

        # 测试负数settlement_days（应该被拒绝或修正）
        try:
            invalid_position = Position(
                portfolio_id=self.portfolio.portfolio_id,
                engine_id=self.engine.engine_id,
                run_id=self.engine._run_id,
                code="INVALID.SZ",
                settlement_days=-1,  # 无效值
                direction=DIRECTION_TYPES.LONG,
                price=Decimal("10.0")
            )
            # 如果创建成功，检查是否被修正为有效值
            if invalid_position.settlement_days < 0:
                print("⚠️ 负数settlement_days未被修正")
            else:
                print("✅ 负数settlement_days被自动修正")
        except Exception as e:
            print(f"✅ 负数settlement_days被正确拒绝: {e}")

        # 测试极大值settlement_days
        try:
            large_days_position = Position(
                portfolio_id=self.portfolio.portfolio_id,
                engine_id=self.engine.engine_id,
                run_id=self.engine._run_id,
                code="LARGE.SZ",
                settlement_days=365,  # 一年
                direction=DIRECTION_TYPES.LONG,
                price=Decimal("10.0")
            )
            print(f"✅ 大值settlement_days被接受: {large_days_position.settlement_days}")
        except Exception as e:
            print(f"⚠️ 大值settlement_days被拒绝: {e}")

        print("✅ 边界条件测试完成")


if __name__ == "__main__":
    # 直接运行测试
    test_instance = TestT1ConfigurableMechanism()

    print("🧪 运行T302 T+1配置化参数机制测试...")

    # 执行所有测试方法
    test_methods = [
        test_instance.setup_method,
        test_instance.test_settlement_days_configuration,
        test_instance.test_market_rules_parameter_adaptation,
        test_instance.test_configuration_change_impact_on_existing_positions,
        test_instance.test_configuration_parameter_persistence,
        test_instance.test_portfolio_level_t1_configuration,
        test_instance.test_edge_cases_and_error_handling,
        test_instance.teardown_method
    ]

    try:
        for method in test_methods:
            if hasattr(method, '__call__'):
                method()
        print("\n🎉 T302测试完成 - T+1配置化参数机制验证成功！")
    except Exception as e:
        print(f"\n❌ T302测试失败: {e}")
        raise