#!/usr/bin/env python3
"""
策略信号生成的业务逻辑验证测试

测试策略基于当前价格数据生成买卖信号的完整业务逻辑，验证：
1. 策略基于价格数据生成信号的正确性
2. 信号的数据完整性和格式正确性
3. 策略参数对信号生成的影响
4. 多策略并行时的信号处理
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import pytest
import datetime
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.strategies.trend_follow import StrategyTrendFollow
from ginkgo.trading.time.providers import LogicalTimeProvider
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, FREQUENCY_TYPES


class TestStrategy(BaseStrategy):
    """测试策略 - 用于验证信号生成业务逻辑"""

    def __init__(self, name="TestStrategy", threshold=Decimal("10.00")):
        super().__init__(name=name)
        self.threshold = threshold
        self.signals_generated = []
        self.call_count = 0
        self.last_portfolio_info = None
        self.last_event = None

    def cal(self, portfolio_info, event, *args, **kwargs):
        """基于价格阈值生成买卖信号"""
        self.call_count += 1
        self.last_portfolio_info = portfolio_info
        self.last_event = event

        signals = []

        if hasattr(event, 'close') and hasattr(event, 'code'):
            current_price = Decimal(str(event.close))

            # 生成买入信号
            if current_price > self.threshold:
                signal = Signal(
                    code=event.code,
                    direction=DIRECTION_TYPES.LONG,
                    reason=f"价格{current_price}突破阈值{self.threshold}",
                    portfolio_id=portfolio_info.get("portfolio_id", "test_portfolio"),
                    engine_id=portfolio_info.get("engine_id", "test_engine"),
                    run_id=portfolio_info.get("run_id", "test_run"),
                    timestamp=portfolio_info.get("now", datetime.datetime.now()),
                    source=SOURCE_TYPES.STRATEGY,
                    strength=0.8,
                    confidence=0.9
                )
                signals.append(signal)
                self.signals_generated.append(signal)

            # 生成卖出信号
            elif current_price < self.threshold - Decimal("2.00"):
                signal = Signal(
                    code=event.code,
                    direction=DIRECTION_TYPES.SHORT,
                    reason=f"价格{current_price}跌破支撑位{self.threshold - Decimal('2.00')}",
                    portfolio_id=portfolio_info.get("portfolio_id", "test_portfolio"),
                    engine_id=portfolio_info.get("engine_id", "test_engine"),
                    run_id=portfolio_info.get("run_id", "test_run"),
                    timestamp=portfolio_info.get("now", datetime.datetime.now()),
                    source=SOURCE_TYPES.STRATEGY,
                    strength=0.7,
                    confidence=0.8
                )
                signals.append(signal)
                self.signals_generated.append(signal)

        return signals


class TestStrategySignalLogic:
    """策略信号生成业务逻辑测试"""

    def setup_method(self):
        """测试前的设置"""
        self.engine = EventEngine()
        self.engine.engine_id = "test_engine_signal_logic"
        self.engine.generate_run_id()

        self.portfolio = PortfolioT1Backtest("test_portfolio")
        self.portfolio.bind_engine(self.engine)

        # 设置时间提供者
        self.time_provider = LogicalTimeProvider(
            initial_time=datetime.datetime(2023, 1, 1, 9, 30, tzinfo=datetime.timezone.utc)
        )
        self.portfolio.set_time_provider(self.time_provider)

    def test_strategy_basic_signal_generation(self):
        """测试策略基本信号生成功能"""
        print("\n🧪 测试策略基本信号生成功能")

        # 创建测试策略
        strategy = TestStrategy(threshold=Decimal("100.00"))
        self.portfolio.add_strategy(strategy)

        # 创建Bar对象
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30, tzinfo=datetime.timezone.utc),
            open=Decimal("100.00"),
            high=Decimal("106.00"),
            low=Decimal("99.50"),
            close=Decimal("105.50"),
            volume=1000000,
            amount=Decimal("105500000"),
            frequency=FREQUENCY_TYPES.DAY
        )

        # 创建价格事件 - 价格高于阈值，应生成买入信号
        price_event = EventPriceUpdate(price_info=bar)

        # 模拟portfolio_info
        portfolio_info = {
            "uuid": "test_portfolio",
            "engine_id": self.engine.engine_id,
            "run_id": self.engine.run_id,
            "now": datetime.datetime(2023, 1, 1, 9, 30, tzinfo=datetime.timezone.utc),
            "positions": {}
        }

        # 调用策略计算
        signals = strategy.cal(portfolio_info, price_event)

        # 验证信号生成
        assert len(signals) == 1, f"预期生成1个信号，实际生成{len(signals)}个"
        assert strategy.call_count == 1, "策略cal方法应被调用1次"

        signal = signals[0]
        assert signal.code == "000001.SZ", "信号代码应为000001.SZ"
        assert signal.direction == DIRECTION_TYPES.LONG, "应为买入信号"
        assert "突破阈值100.00" in signal.reason, "信号原因应包含突破信息"
        assert signal.portfolio_id == "test_portfolio", "投资组合ID应正确"
        assert signal.engine_id == self.engine.engine_id, "引擎ID应正确"
        assert signal.source == SOURCE_TYPES.STRATEGY, "信号来源应为策略"
        assert signal.strength == 0.8, "信号强度应为0.8"
        assert signal.confidence == 0.9, "信号置信度应为0.9"

        print("✅ 基本信号生成功能测试通过")

    def test_strategy_signal_data_integrity(self):
        """测试信号数据完整性和格式正确性"""
        print("\n🧪 测试信号数据完整性和格式正确性")

        strategy = TestStrategy(threshold=Decimal("50.00"))

        # 创建多个价格事件测试不同场景
        test_cases = [
            {
                "price": Decimal("55.00"),
                "expected_direction": DIRECTION_TYPES.LONG,
                "expected_reason_contains": "突破阈值50.00"
            },
            {
                "price": Decimal("47.00"),
                "expected_direction": DIRECTION_TYPES.SHORT,
                "expected_reason_contains": "跌破支撑位48.00"
            },
            {
                "price": Decimal("49.00"),
                "expected_signals": 0,
                "description": "价格在阈值附近，不应生成信号"
            }
        ]

        portfolio_info = {
            "uuid": "test_portfolio",
            "engine_id": self.engine.engine_id,
            "run_id": self.engine.run_id,
            "now": datetime.datetime(2023, 1, 1, 9, 30, tzinfo=datetime.timezone.utc),
            "positions": {}
        }

        for i, case in enumerate(test_cases):
            print(f"  测试场景 {i+1}: 价格={case['price']}")

                # 创建Bar对象
            bar = Bar(
                code="000002.SZ",
                timestamp=datetime.datetime(2023, 1, 1, 9, 30 + i, tzinfo=datetime.timezone.utc),
                open=case["price"] - Decimal("1.00"),
                high=case["price"] + Decimal("0.50"),
                low=case["price"] - Decimal("1.50"),
                close=case["price"],
                volume=500000,
                amount=case["price"] * 500000,
                frequency=FREQUENCY_TYPES.DAY
            )

            price_event = EventPriceUpdate(price_info=bar)

            signals = strategy.cal(portfolio_info, price_event)

            if "expected_signals" in case:
                assert len(signals) == case["expected_signals"], \
                    f"预期生成{case['expected_signals']}个信号，实际生成{len(signals)}个"
            else:
                assert len(signals) == 1, f"预期生成1个信号，实际生成{len(signals)}个"

                signal = signals[0]
                assert signal.code == "000002.SZ", "信号代码应正确"
                assert signal.direction == case["expected_direction"], \
                    f"信号方向应为{case['expected_direction']}"
                assert case["expected_reason_contains"] in signal.reason, \
                    f"信号原因应包含: {case['expected_reason_contains']}"

                # 验证信号数据完整性
                assert signal.is_valid(), "生成的信号应该有效"
                assert signal.portfolio_id, "投资组合ID不应为空"
                assert signal.engine_id, "引擎ID不应为空"
                assert signal.timestamp, "时间戳不应为空"
                assert 0.0 <= signal.strength <= 1.0, "信号强度应在0-1范围内"
                assert 0.0 <= signal.confidence <= 1.0, "信号置信度应在0-1范围内"

        print("✅ 信号数据完整性和格式正确性测试通过")

    def test_strategy_parameter_influence(self):
        """测试策略参数对信号生成的影响"""
        print("\n🧪 测试策略参数对信号生成的影响")

        # 测试不同阈值的策略
        strategies = [
            TestStrategy(name="LowThreshold", threshold=Decimal("30.00")),
            TestStrategy(name="HighThreshold", threshold=Decimal("70.00")),
            TestStrategy(name="MediumThreshold", threshold=Decimal("50.00"))
        ]

        # 使用固定价格测试
        test_price = Decimal("55.00")
        bar = Bar(
            code="000003.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30, tzinfo=datetime.timezone.utc),
            open=Decimal("54.00"),
            high=Decimal("55.50"),
            low=Decimal("53.50"),
            close=test_price,
            volume=800000,
            amount=test_price * 800000,
            frequency=FREQUENCY_TYPES.DAY
        )
        price_event = EventPriceUpdate(price_info=bar)

        portfolio_info = {
            "uuid": "test_portfolio",
            "engine_id": self.engine.engine_id,
            "run_id": self.engine.run_id,
            "now": datetime.datetime(2023, 1, 1, 9, 30, tzinfo=datetime.timezone.utc),
            "positions": {}
        }

        expected_results = [
            {"threshold": "30.00", "should_generate": True, "direction": DIRECTION_TYPES.LONG},
            {"threshold": "70.00", "should_generate": True, "direction": DIRECTION_TYPES.SHORT},
            {"threshold": "50.00", "should_generate": True, "direction": DIRECTION_TYPES.LONG}
        ]

        for strategy, expected in zip(strategies, expected_results):
            print(f"  测试策略 {strategy.name}, 阈值={expected['threshold']}, 实际阈值={strategy.threshold}")

            signals = strategy.cal(portfolio_info, price_event)

            if expected["should_generate"]:
                assert len(signals) == 1, \
                    f"策略{strategy.name}应生成1个信号，实际生成{len(signals)}个"

                signal = signals[0]
                assert signal.direction == expected["direction"], \
                    f"策略{strategy.name}的信号方向应为{expected['direction']}"
                # 验证信号原因包含相关信息
                if expected["direction"] == DIRECTION_TYPES.LONG:
                    assert f"突破阈值{expected['threshold']}" in signal.reason, \
                        f"买入信号原因应包含'突破阈值{expected['threshold']}'"
                else:
                    support_level = Decimal(expected['threshold']) - Decimal("2.00")
                    assert f"跌破支撑位{support_level}" in signal.reason, \
                        f"卖出信号原因应包含'跌破支撑位{support_level}'"

                print(f"    ✅ 生成{signal.direction.value}信号")
            else:
                assert len(signals) == 0, \
                    f"策略{strategy.name}不应生成信号，实际生成{len(signals)}个"
                print(f"    ✅ 未生成信号（符合预期）")

        print("✅ 策略参数对信号生成的影响测试通过")

    def test_multi_strategy_parallel_processing(self):
        """测试多策略并行时的信号处理"""
        print("\n🧪 测试多策略并行时的信号处理")

        # 创建多个不同类型的策略
        strategies = [
            TestStrategy(name="StrategyA", threshold=Decimal("40.00")),
            TestStrategy(name="StrategyB", threshold=Decimal("60.00")),
            TestStrategy(name="StrategyC", threshold=Decimal("50.00"))
        ]

        # 将所有策略添加到投资组合
        for strategy in strategies:
            self.portfolio.add_strategy(strategy)

        # 创建价格事件
        bar = Bar(
            code="000004.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30, tzinfo=datetime.timezone.utc),
            open=Decimal("54.50"),
            high=Decimal("55.80"),
            low=Decimal("54.00"),
            close=Decimal("55.00"),
            volume=1200000,
            amount=Decimal("66000000"),
            frequency=FREQUENCY_TYPES.DAY
        )
        price_event = EventPriceUpdate(price_info=bar)

        portfolio_info = {
            "uuid": "test_portfolio",
            "engine_id": self.engine.engine_id,
            "run_id": self.engine.run_id,
            "now": datetime.datetime(2023, 1, 1, 9, 30, tzinfo=datetime.timezone.utc),
            "positions": {}
        }

        # 并行调用所有策略
        all_signals = []
        strategy_results = {}

        for strategy in strategies:
            print(f"  策略 {strategy.name}, 阈值={strategy.threshold}")
            signals = strategy.cal(portfolio_info, price_event)
            strategy_results[strategy.name] = signals
            all_signals.extend(signals)
            print(f"    生成信号数量: {len(signals)}")

        # 验证每个策略的独立信号生成
        expected_signals = {
            "StrategyA": {"generate": True, "direction": DIRECTION_TYPES.LONG},   # 55 > 40，应生成买入信号
            "StrategyB": {"generate": True, "direction": DIRECTION_TYPES.SHORT}, # 55 < 58 (60-2)，应生成卖出信号
            "StrategyC": {"generate": True, "direction": DIRECTION_TYPES.LONG}    # 55 > 50，应生成买入信号
        }

        for strategy_name, expected_info in expected_signals.items():
            signals = strategy_results[strategy_name]
            if expected_info["generate"]:
                assert len(signals) == 1, \
                    f"{strategy_name}应生成1个信号，实际生成{len(signals)}个"
                assert signals[0].direction == expected_info["direction"], \
                    f"{strategy_name}应生成{expected_info['direction'].value}信号，实际生成{signals[0].direction.value}"
                signal_direction = "买入" if signals[0].direction == DIRECTION_TYPES.LONG else "卖出"
                print(f"  ✅ {strategy_name}: 生成{signal_direction}信号")
            else:
                assert len(signals) == 0, \
                    f"{strategy_name}不应生成信号，实际生成{len(signals)}个"
                print(f"  ✅ {strategy_name}: 未生成信号")

        # 验证信号的总数和独立性
        total_expected_signals = sum(1 for info in expected_signals.values() if info["generate"])
        assert len(all_signals) == total_expected_signals, \
            f"预期总共生成{total_expected_signals}个信号，实际生成{len(all_signals)}个"

        # 验证每个信号都有唯一的原因（基于不同策略的阈值）
        signal_reasons = [signal.reason for signal in all_signals]
        assert len(signal_reasons) == len(set(signal_reasons)), \
            "每个信号的原因应该是唯一的"

        print("✅ 多策略并行时的信号处理测试通过")

    # NOTE: 真实策略信号生成测试已在 test_signal_t1_delay.py::test_strategy_signal_generation 中完成
# 避免重复测试，此处移除该测试用例

    def test_signal_generation_edge_cases(self):
        """测试信号生成的边界情况"""
        print("\n🧪 测试信号生成的边界情况")

        strategy = TestStrategy(threshold=Decimal("100.00"))

        portfolio_info = {
            "uuid": "test_portfolio",
            "engine_id": self.engine.engine_id,
            "run_id": self.engine.run_id,
            "now": datetime.datetime(2023, 1, 1, 9, 30, tzinfo=datetime.timezone.utc),
            "positions": {}
        }

        # 测试边界情况
        edge_cases = [
            {
                "name": "价格正好等于阈值",
                "price": Decimal("100.00"),
                "expected_signals": 0
            },
            {
                "name": "价格略高于阈值",
                "price": Decimal("100.01"),
                "expected_signals": 1,
                "expected_direction": DIRECTION_TYPES.LONG
            },
            {
                "name": "价格略低于阈值减2元",
                "price": Decimal("97.99"),
                "expected_signals": 1,
                "expected_direction": DIRECTION_TYPES.SHORT
            },
            {
                "name": "价格等于阈值减2元",
                "price": Decimal("98.00"),
                "expected_signals": 0
            }
        ]

        for case in edge_cases:
            print(f"  测试: {case['name']} (价格={case['price']})")

            bar = Bar(
                code="000006.SZ",
                timestamp=datetime.datetime(2023, 1, 1, 9, 30, tzinfo=datetime.timezone.utc),
                open=case["price"],
                high=case["price"],
                low=case["price"],
                close=case["price"],
                volume=100000,
                amount=case["price"] * 100000,
                frequency=FREQUENCY_TYPES.DAY
            )
            price_event = EventPriceUpdate(price_info=bar)

            signals = strategy.cal(portfolio_info, price_event)

            assert len(signals) == case["expected_signals"], \
                f"{case['name']}: 预期{case['expected_signals']}个信号，实际{len(signals)}个"

            if case["expected_signals"] > 0:
                assert signals[0].direction == case["expected_direction"], \
                    f"{case['name']}: 信号方向应为{case['expected_direction']}"

            print(f"    ✅ {case['name']}测试通过")

        print("✅ 信号生成边界情况测试通过")


if __name__ == "__main__":
    # 运行测试
    test_instance = TestStrategySignalLogic()

    test_methods = [
        test_instance.test_strategy_basic_signal_generation,
        test_instance.test_strategy_signal_data_integrity,
        test_instance.test_strategy_parameter_influence,
        test_instance.test_multi_strategy_parallel_processing,
        test_instance.test_signal_generation_edge_cases
    ]

    passed_tests = 0
    total_tests = len(test_methods)

    for test_method in test_methods:
        try:
            test_instance.setup_method()
            test_method()
            passed_tests += 1
        except Exception as e:
            print(f"❌ 测试失败: {test_method.__name__}")
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n📊 测试结果: {passed_tests}/{total_tests} 通过")

    if passed_tests == total_tests:
        print("🎉 所有策略信号生成业务逻辑测试通过！")
        print("💡 策略信号生成功能正常，可以正确处理各种业务场景")
    else:
        print("⚠️  部分测试失败，需要检查策略信号生成逻辑")
        sys.exit(1)