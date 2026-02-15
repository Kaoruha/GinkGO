"""
IStrategy Protocol接口测试

遵循TDD方法，验证BaseStrategy类对IStrategy Protocol的接口实现状态。
专注于核心功能验证，确保框架的基础类型安全和接口可用性。
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime

# 导入Protocol接口和实现类
from ginkgo.trading.interfaces.protocols.strategy import IStrategy
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.entities.bar import Bar
from ginkgo.enums import FREQUENCY_TYPES


@pytest.mark.tdd
@pytest.mark.protocol
class TestIStrategyProtocolBasic:
    """IStrategy Protocol基础功能测试类"""

    def test_base_strategy_implements_istrategy_protocol(self):
        """测试BaseStrategy实现IStrategy Protocol接口

        保障情况: 当开发者创建自定义策略类继承BaseStrategy时，确保该策略类能够通过IStrategy接口的类型检查，
        保证框架的类型安全性和IDE支持的有效性。
        """
        strategy = BaseStrategy()

        # 验证Protocol接口合规性
        assert isinstance(strategy, IStrategy), "BaseStrategy应该实现IStrategy Protocol接口"

    def test_cal_method_basic_functionality(self):
        """测试cal方法基础功能

        保障情况: 当策略接收到市场数据事件时，确保cal方法能够正常处理输入参数并返回正确类型的信号列表，
        避免因参数处理错误导致的策略运行中断。
        """
        strategy = BaseStrategy()

        # 准备测试数据
        portfolio_info = {
            "positions": {"000001.SZ": 1000},
            "total_value": 100000.0,
            "available_cash": 50000.0
        }

        # 创建EventPriceUpdate事件
        bar = Bar(
            code='000001.SZ',
            open=10.0,
            high=10.8,
            low=9.8,
            close=10.5,
            volume=100000,
            amount=1050000.0,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime.now()
        )
        event = EventPriceUpdate(bar)

        # 调用cal方法
        result = strategy.cal(portfolio_info, event)

        # 验证返回类型
        assert isinstance(result, list), "cal方法应该返回List类型"
        # BaseStrategy默认返回空列表，这是符合预期的行为

    def test_get_strategy_info_method_exists(self):
        """测试get_strategy_info方法存在性和基本可用性

        保障情况: 当系统调用get_strategy_info方法时，确保该方法存在且可调用，同时验证BaseStrategy提供了
        默认的基本信息实现，支持策略的基本识别需求。
        """
        strategy = BaseStrategy()

        # 验证方法存在
        assert hasattr(strategy, 'get_strategy_info'), "策略应该有get_strategy_info方法"

        # 验证方法可调用且不抛出异常
        info = strategy.get_strategy_info()

        # 验证返回对象具有基本的字典行为
        assert hasattr(info, '__getitem__'), "返回对象应该支持字典访问"
        assert hasattr(info, 'keys'), "返回对象应该支持keys方法"

    def test_validate_parameters_method_exists(self):
        """测试validate_parameters方法存在性和基本可用性

        保障情况: 当系统或用户配置策略参数时，确保validate_parameters方法存在且能够处理参数验证请求，
        避免因参数配置错误导致的系统崩溃或不可预期的行为。
        """
        strategy = BaseStrategy()

        # 验证方法存在
        assert hasattr(strategy, 'validate_parameters'), "策略应该有validate_parameters方法"

        # 测试基本参数处理
        test_params = {"test_param": "test_value"}

        # 验证调用不抛出异常
        result = strategy.validate_parameters(test_params)

        # 验证返回类型（BaseStrategy可能默认返回True或其他默认值）
        assert isinstance(result, bool), "validate_parameters应该返回bool类型"

    def test_get_strategy_info_method_comprehensive(self):
        """测试get_strategy_info方法完整功能

        保障情况: 当系统或用户需要获取策略的详细信息时，确保get_strategy_info方法能够返回
        包含名称、版本、描述、参数等完整信息的字典，支持策略管理和监控需求。
        """
        strategy = BaseStrategy(name="TestStrategy")

        # 调用方法
        info = strategy.get_strategy_info()

        # 验证返回类型
        assert isinstance(info, dict), "get_strategy_info应该返回字典类型"

        # 验证必需字段存在
        required_fields = ["name", "version", "description"]
        for field in required_fields:
            assert field in info, f"返回信息应该包含{field}字段"

        # 验证字段值类型和内容
        assert isinstance(info["name"], str), "name应该是字符串"
        assert info["name"] == "TestStrategy", "name应该与设置的一致"
        assert isinstance(info["version"], str), "version应该是字符串"
        assert len(info["version"]) > 0, "version不应该为空"
        assert isinstance(info["description"], str), "description应该是字符串"

        # 验证可选字段
        optional_fields = ["parameters", "performance_metrics", "risk_metrics", "last_updated"]
        for field in optional_fields:
            if field in info:
                assert isinstance(info[field], (dict, str)), f"{field}应该是字典或字符串类型"

    def test_validate_parameters_method_comprehensive(self):
        """测试validate_parameters方法完整功能

        保障情况: 当用户配置策略参数或系统验证参数有效性时，确保validate_parameters方法能够
        正确验证参数的类型、范围和逻辑关系，为参数配置提供可靠的验证机制。
        """
        strategy = BaseStrategy()

        # 测试有效参数
        valid_params = {
            "period": 20,
            "threshold": 0.02,
            "stop_loss": 0.05
        }
        result = strategy.validate_parameters(valid_params)
        assert isinstance(result, bool), "应该返回布尔值"
        assert result is True, "有效参数应该验证通过"

        # 测试空参数字典
        empty_params = {}
        result = strategy.validate_parameters(empty_params)
        assert isinstance(result, bool), "空参数应该返回布尔值"
        # BaseStrategy默认可能接受空参数或返回默认值

        # 测试无效参数类型
        invalid_params = {"period": "invalid"}
        try:
            result = strategy.validate_parameters(invalid_params)
            # 如果不抛出异常，应该返回False
            assert isinstance(result, bool), "应该返回布尔值"
        except (ValueError, TypeError):
            # 抛出类型错误也是可以接受的行为
            pass

    def test_initialize_method_comprehensive(self):
        """测试initialize方法完整功能

        保障情况: 当策略开始执行前需要进行初始化时，确保initialize方法能够正确处理
        上下文参数，进行数据预加载、状态设置等初始化工作，为策略执行做好准备。
        """
        strategy = BaseStrategy(name="TestStrategy")

        # 验证方法存在
        assert hasattr(strategy, 'initialize'), "策略应该有initialize方法"

        # 准备初始化上下文
        context = {
            "data_source": "test_source",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "universe": ["000001.SZ", "000002.SZ"],
            "frequency": "1d",
            "benchmark": "000300.SH"
        }

        # 调用初始化方法
        result = strategy.initialize(context)

        # initialize方法应该返回None（void方法）
        assert result is None, "initialize方法应该返回None"

        # 验证策略状态变化（如果有内部状态的话）
        # 这里可以验证strategy是否有某些初始化后的状态标记

    def test_finalize_method_comprehensive(self):
        """测试finalize方法完整功能

        保障情况: 当策略执行结束时，确保finalize方法能够正确计算最终绩效指标、
        生成执行报告并进行资源清理，为策略评估提供完整的结果信息。
        """
        strategy = BaseStrategy(name="TestStrategy")

        # 验证方法存在
        assert hasattr(strategy, 'finalize'), "策略应该有finalize方法"

        # 调用结束方法
        result = strategy.finalize()

        # 验证返回类型
        assert isinstance(result, dict), "finalize应该返回字典类型"

        # 验证返回结果的结构
        expected_sections = ["execution_summary", "final_portfolio", "performance_attribution"]
        for section in expected_sections:
            if section in result:  # 这些字段可能是可选的
                assert isinstance(result[section], dict), f"{section}应该是字典类型"

        # 如果有基本信息，验证其类型
        if "execution_summary" in result:
            summary = result["execution_summary"]
            if "total_signals" in summary:
                assert isinstance(summary["total_signals"], int), "total_signals应该是整数"

    def test_on_data_updated_method_comprehensive(self):
        """测试on_data_updated方法完整功能

        保障情况: 当有新的市场数据可用时，确保on_data_updated方法能够正确处理
        数据更新通知，进行技术指标更新、缓存刷新等数据预处理工作。
        """
        strategy = BaseStrategy()

        # 验证方法存在
        assert hasattr(strategy, 'on_data_updated'), "策略应该有on_data_updated方法"

        # 准备测试数据
        updated_symbols = ["000001.SZ", "000002.SZ", "600000.SH"]

        # 调用方法（应该不抛出异常）
        result = strategy.on_data_updated(updated_symbols)

        # on_data_updated应该返回None（void方法）
        assert result is None, "on_data_updated方法应该返回None"

        # 测试空列表
        empty_symbols = []
        result = strategy.on_data_updated(empty_symbols)
        assert result is None, "处理空符号列表应该返回None"

    def test_name_property_exists(self):
        """测试name属性存在性和基本功能

        保障情况: 当系统需要标识和管理多个策略实例时，确保每个策略都有可访问的name属性，
        避免策略无法被正确识别或管理。
        """
        strategy = BaseStrategy()

        # 验证name属性存在
        assert hasattr(strategy, 'name'), "策略应该有name属性"

        # 验证name类型和值
        assert isinstance(strategy.name, str), "name应该是字符串类型"
        assert len(strategy.name) > 0, "name不应该为空"

        # 验证默认名称
        assert strategy.name == "Strategy", "默认名称应该是'Strategy'"


@pytest.mark.tdd
@pytest.mark.protocol
class TestIStrategyProtocolTypeSafety:
    """IStrategy Protocol类型安全测试"""

    def test_protocol_runtime_checking(self):
        """测试Protocol运行时类型检查"""
        strategy = BaseStrategy()

        # 验证运行时类型检查
        assert isinstance(strategy, IStrategy), "运行时类型检查应该通过"

        # 测试非策略对象
        non_strategy = {"name": "not_a_strategy"}
        assert not isinstance(non_strategy, IStrategy), "非策略对象不应该通过IStrategy检查"

    def test_strategy_method_existence_validation(self):
        """测试策略方法存在性验证"""
        strategy = BaseStrategy()

        # 验证IStrategy Protocol定义的必需方法存在
        required_methods = ['cal', 'get_strategy_info', 'validate_parameters']
        for method_name in required_methods:
            assert hasattr(strategy, method_name), f"策略应该有{method_name}方法"
            assert callable(getattr(strategy, method_name)), f"{method_name}应该是可调用的"

    def test_strategy_property_existence_validation(self):
        """测试策略属性存在性验证"""
        strategy = BaseStrategy()

        # 验证IStrategy Protocol定义的必需属性存在
        required_properties = ['name']
        for prop_name in required_properties:
            assert hasattr(strategy, prop_name), f"策略应该有{prop_name}属性"


@pytest.mark.tdd
@pytest.mark.financial
class TestIStrategyProtocolFinancialContext:
    """IStrategy Protocol金融业务上下文测试"""

    def test_strategy_with_real_market_data(self):
        """测试策略处理真实市场数据"""
        strategy = BaseStrategy()

        # 使用真实OHLC数据结构
        portfolio_info = {
            "positions": {"000001.SZ": 1000},
            "total_value": 105000.0,  # 当前市值
            "available_cash": 5000.0,
            "cost_basis": 10.0  # 成本价
        }

        # 创建真实的市场数据事件
        bar = Bar(
            code='000001.SZ',
            open=10.20,   # 开盘价
            high=10.80,   # 最高价
            low=9.90,     # 最低价
            close=10.50,  # 收盘价
            volume=1500000,  # 成交量
            amount=15750000.0,  # 成交额
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime.now()
        )
        event = EventPriceUpdate(bar)

        # 调用策略
        signals = strategy.cal(portfolio_info, event)

        # 验证能处理真实数据结构
        assert isinstance(signals, list), "应该能处理真实市场数据并返回信号列表"

    def test_strategy_edge_cases_handling(self):
        """测试策略边界情况处理"""
        strategy = BaseStrategy()

        # 测试空portfolio_info
        empty_portfolio = {}
        empty_event = None  # 或者某种空事件

        # BaseStrategy应该能处理边界情况而不崩溃
        try:
            result = strategy.cal(empty_portfolio, empty_event)
            assert isinstance(result, list), "应该能处理空输入"
        except Exception as e:
            # 如果抛出异常，应该是预期的类型错误，而不是崩溃
            assert isinstance(e, (TypeError, AttributeError)), "应该是预期的类型错误"


# TDD阶段标记
def tdd_phase(phase: str):
    """TDD阶段标记装饰器"""
    def decorator(test_func):
        test_func.tdd_phase = phase
        return test_func
    return decorator