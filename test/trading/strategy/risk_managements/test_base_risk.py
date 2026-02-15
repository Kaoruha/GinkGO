"""
BaseRiskManagement类TDD测试

通过TDD方式开发BaseRiskManagement风控管理基类的完整测试套件
涵盖订单处理和主动风控信号生成功能
"""
import pytest
import sys
from pathlib import Path

# 导入BaseRiskManagement类和相关依赖
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from datetime import datetime


@pytest.mark.unit
class TestBaseRiskManagementConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认参数构造"""
        risk_manager = BaseRiskManagement()

        # 验证name默认为"baseriskmanagement"
        assert risk_manager.name == "baseriskmanagement"

        # 验证_data_feeder初始化为None
        assert risk_manager._data_feeder is None

        # 验证继承自BacktestBase的属性
        assert hasattr(risk_manager, 'engine_id')
        assert hasattr(risk_manager, 'portfolio_id')
        assert hasattr(risk_manager, 'run_id')

    def test_named_constructor(self):
        """测试命名构造"""
        custom_name = "StopLossRisk"
        risk_manager = BaseRiskManagement(name=custom_name)

        # 验证name被正确设置
        assert risk_manager.name == custom_name
        assert risk_manager.name == "StopLossRisk"

    def test_backtest_base_inheritance(self):
        """测试BacktestBase类继承"""
        risk_manager = BaseRiskManagement()

        # 验证正确继承BacktestBase的方法
        assert hasattr(risk_manager, 'set_backtest_ids')
        assert hasattr(risk_manager, 'get_id_dict')
        assert hasattr(risk_manager, 'bind_engine')
        assert hasattr(risk_manager, 'set_name')
        assert hasattr(risk_manager, 'log')

        # 验证ID管理属性
        assert risk_manager.engine_id == ""
        assert risk_manager.portfolio_id == ""
        assert risk_manager.run_id == ""

        # 验证日志功能
        assert hasattr(risk_manager, 'loggers')
        assert len(risk_manager.loggers) > 0  # 默认添加了GLOG

    def test_data_feeder_initialization(self):
        """测试数据接口初始化"""
        risk_manager = BaseRiskManagement()

        # 验证_data_feeder初始值为None
        assert risk_manager._data_feeder is None
        assert not hasattr(risk_manager, 'data_feeder')  # 确保私有属性

    def test_args_kwargs_handling(self):
        """测试参数传递处理"""
        # 测试传递额外参数
        risk_manager = BaseRiskManagement(name="TestRisk", test_param="test_value")

        # 验证name参数正确传递
        assert risk_manager.name == "TestRisk"

        # 验证基础功能仍然正常
        assert hasattr(risk_manager, 'set_backtest_ids')
        assert risk_manager._data_feeder is None

    def test_risk_manager_uuid_generation(self):
        """测试风控管理器UUID生成"""
        risk_manager1 = BaseRiskManagement()
        risk_manager2 = BaseRiskManagement()

        # 验证每个实例都有UUID
        assert hasattr(risk_manager1, 'uuid')
        assert hasattr(risk_manager2, 'uuid')

        # 验证UUID不为空且唯一
        assert risk_manager1.uuid is not None
        assert risk_manager2.uuid is not None
        assert risk_manager1.uuid != risk_manager2.uuid

        # 验证UUID是字符串类型
        assert isinstance(risk_manager1.uuid, str)
        assert isinstance(risk_manager2.uuid, str)

    def test_multiple_instances_independence(self):
        """测试多实例独立性"""
        # 创建多个风控管理器实例
        risk_manager1 = BaseRiskManagement(name="Risk1")
        risk_manager2 = BaseRiskManagement(name="Risk2")

        # 验证实例独立性
        risk_manager1.set_backtest_ids(engine_id="engine1", portfolio_id="portfolio1", run_id="run1")
        risk_manager2.set_backtest_ids(engine_id="engine2", portfolio_id="portfolio2", run_id="run2")

        # 验证各自独立设置
        assert risk_manager1.engine_id == "engine1"
        assert risk_manager1.portfolio_id == "portfolio1"
        assert risk_manager1.run_id == "run1"

        assert risk_manager2.engine_id == "engine2"
        assert risk_manager2.portfolio_id == "portfolio2"
        assert risk_manager2.run_id == "run2"

        # 验证名称独立性
        assert risk_manager1.name == "Risk1"
        assert risk_manager2.name == "Risk2"


@pytest.mark.unit
class TestBaseRiskManagementProperties:
    """2. 属性访问测试"""

    def test_name_property(self):
        """测试风控管理器名称属性"""
        # 测试默认名称
        risk_manager = BaseRiskManagement()
        assert risk_manager.name == "baseriskmanagement"

        # 测试自定义名称
        custom_risk = BaseRiskManagement(name="CustomRisk")
        assert custom_risk.name == "CustomRisk"

        # 测试名称可读性
        assert isinstance(risk_manager.name, str)
        assert len(risk_manager.name) > 0

    def test_data_feeder_property(self):
        """测试数据接口属性"""
        risk_manager = BaseRiskManagement()

        # 测试初始状态
        assert risk_manager._data_feeder is None

        # 创建模拟数据接口
        class MockDataFeeder:
            def __init__(self):
                self.name = "MockFeeder"

        mock_feeder = MockDataFeeder()

        # 测试绑定后状态
        risk_manager.bind_data_feeder(mock_feeder)
        assert risk_manager._data_feeder is mock_feeder
        assert risk_manager._data_feeder.name == "MockFeeder"

        # 测试可以重新绑定
        class AnotherMockFeeder:
            def __init__(self):
                self.name = "AnotherFeeder"

        another_feeder = AnotherMockFeeder()
        risk_manager.bind_data_feeder(another_feeder)
        assert risk_manager._data_feeder is another_feeder
        assert risk_manager._data_feeder.name == "AnotherFeeder"

    def test_inherited_properties(self):
        """测试继承属性"""
        risk_manager = BaseRiskManagement(name="TestRisk")

        # 测试从BacktestBase继承的ID相关属性
        assert hasattr(risk_manager, 'engine_id')
        assert hasattr(risk_manager, 'portfolio_id')
        assert hasattr(risk_manager, 'run_id')
        assert hasattr(risk_manager, 'uuid')

        # 测试从TimeRelated继承的时间相关属性
        assert hasattr(risk_manager, 'timestamp')

        # 验证初始值
        assert risk_manager.engine_id == ""
        assert risk_manager.portfolio_id == ""
        assert risk_manager.run_id == ""
        assert risk_manager.uuid is not None

        # 测试设置后的值
        risk_manager.set_backtest_ids(engine_id="test_engine", portfolio_id="test_portfolio", run_id="test_run")
        assert risk_manager.engine_id == "test_engine"
        assert risk_manager.portfolio_id == "test_portfolio"
        assert risk_manager.run_id == "test_run"

    def test_property_immutability(self):
        """测试属性不可变性"""
        risk_manager = BaseRiskManagement(name="FixedName")

        # 测试name属性可以修改（通过set_name方法）
        original_name = risk_manager.name
        risk_manager.set_name("NewName")
        assert risk_manager.name == "NewName"
        assert risk_manager.name != original_name

        # 测试_data_feeder可以通过bind_data_feeder方法修改
        class MockFeeder:
            pass

        assert risk_manager._data_feeder is None
        mock_feeder = MockFeeder()
        risk_manager.bind_data_feeder(mock_feeder)
        assert risk_manager._data_feeder is mock_feeder

        # 测试ID属性可以通过set_backtest_ids修改
        risk_manager.set_backtest_ids(engine_id="engine1", portfolio_id="portfolio1", run_id="run1")
        assert risk_manager.engine_id == "engine1"
        assert risk_manager.portfolio_id == "portfolio1"
        assert risk_manager.run_id == "run1"

    def test_property_type_validation(self):
        """测试属性类型验证"""
        risk_manager = BaseRiskManagement(name="TypeTest")

        # 验证name属性类型
        assert isinstance(risk_manager.name, str)

        # 验证ID属性类型
        assert isinstance(risk_manager.engine_id, str)
        assert isinstance(risk_manager.portfolio_id, str)
        assert isinstance(risk_manager.run_id, str)
        assert isinstance(risk_manager.uuid, str)

        # 验证_data_feeder初始类型为None
        assert risk_manager._data_feeder is None

        # 绑定后验证类型
        class MockFeeder:
            pass

        mock_feeder = MockFeeder()
        risk_manager.bind_data_feeder(mock_feeder)
        assert risk_manager._data_feeder is mock_feeder

    def test_runtime_property_access(self):
        """测试运行时属性状态"""
        risk_manager = BaseRiskManagement(name="RuntimeTest")

        # 测试初始运行时状态
        assert risk_manager.name == "RuntimeTest"
        assert risk_manager._data_feeder is None
        assert risk_manager.engine_id == ""
        assert risk_manager.portfolio_id == ""
        assert risk_manager.run_id == ""

        # 模拟运行时状态变化
        class RuntimeFeeder:
            def __init__(self):
                self.runtime_data = "test_data"

        # 绑定数据接口
        runtime_feeder = RuntimeFeeder()
        risk_manager.bind_data_feeder(runtime_feeder)

        # 设置运行时ID
        risk_manager.set_backtest_ids(engine_id="runtime_engine", portfolio_id="runtime_portfolio", run_id="runtime_run")

        # 验证运行时状态
        assert risk_manager._data_feeder is runtime_feeder
        assert risk_manager._data_feeder.runtime_data == "test_data"
        assert risk_manager.engine_id == "runtime_engine"
        assert risk_manager.portfolio_id == "runtime_portfolio"
        assert risk_manager.run_id == "runtime_run"

        # 验证日志功能在运行时可用
        assert hasattr(risk_manager, 'log')
        assert hasattr(risk_manager, 'loggers')
        assert callable(risk_manager.log)


@pytest.mark.unit
class TestBaseRiskManagementDataSetting:
    """3. 数据设置测试"""

    def test_data_feeder_binding(self):
        """测试数据接口绑定"""
        risk_manager = BaseRiskManagement(name="BindingTest")

        # 测试初始状态
        assert risk_manager._data_feeder is None

        # 创建模拟数据接口
        class MockDataFeeder:
            def __init__(self, name="TestFeeder"):
                self.name = name
                self.data_ready = True

            def get_market_data(self):
                return {"price": 100.0, "volume": 1000}

        # 测试绑定
        mock_feeder = MockDataFeeder()
        risk_manager.bind_data_feeder(mock_feeder)

        # 验证绑定成功
        assert risk_manager._data_feeder is mock_feeder
        assert risk_manager._data_feeder.name == "TestFeeder"
        assert risk_manager._data_feeder.data_ready is True

        # 验证可以访问数据接口方法
        market_data = risk_manager._data_feeder.get_market_data()
        assert market_data["price"] == 100.0
        assert market_data["volume"] == 1000

    def test_data_feeder_rebinding(self):
        """测试数据接口重绑定"""
        risk_manager = BaseRiskManagement()

        # 创建第一个数据接口
        class FirstFeeder:
            def __init__(self):
                self.name = "FirstFeeder"
                self.version = 1

        # 创建第二个数据接口
        class SecondFeeder:
            def __init__(self):
                self.name = "SecondFeeder"
                self.version = 2

        # 绑定第一个接口
        first_feeder = FirstFeeder()
        risk_manager.bind_data_feeder(first_feeder)
        assert risk_manager._data_feeder is first_feeder
        assert risk_manager._data_feeder.version == 1

        # 重绑定到第二个接口
        second_feeder = SecondFeeder()
        risk_manager.bind_data_feeder(second_feeder)

        # 验证重绑定成功
        assert risk_manager._data_feeder is second_feeder
        assert risk_manager._data_feeder.version == 2
        assert risk_manager._data_feeder.name == "SecondFeeder"

        # 确保不再引用第一个接口
        assert risk_manager._data_feeder is not first_feeder

    def test_data_feeder_validation(self):
        """测试数据接口验证"""
        risk_manager = BaseRiskManagement()

        # 测试绑定None（应该允许）
        risk_manager.bind_data_feeder(None)
        assert risk_manager._data_feeder is None

        # 测试绑定简单对象（基类不进行严格验证）
        class SimpleFeeder:
            def __init__(self):
                self.name = "Simple"

        simple_feeder = SimpleFeeder()
        risk_manager.bind_data_feeder(simple_feeder)
        assert risk_manager._data_feeder is simple_feeder
        assert risk_manager._data_feeder.name == "Simple"

        # 测试绑定字典对象（也允许）
        dict_feeder = {"name": "DictFeeder", "type": "mock"}
        risk_manager.bind_data_feeder(dict_feeder)
        assert risk_manager._data_feeder is dict_feeder
        assert risk_manager._data_feeder["name"] == "DictFeeder"

    def test_risk_parameters_setting(self):
        """测试风控参数设置"""
        # 创建一个自定义风控管理器来测试参数设置
        class CustomRiskManager(BaseRiskManagement):
            def __init__(self, **kwargs):
                super().__init__(name="CustomRisk", **kwargs)
                self.max_position_ratio = 0.1  # 默认最大持仓比例
                self.stop_loss_rate = 0.05     # 默认止损率
                self.custom_params = {}        # 自定义参数存储

            def set_risk_param(self, key, value):
                """设置风控参数"""
                self.custom_params[key] = value

            def get_risk_param(self, key, default=None):
                """获取风控参数"""
                return self.custom_params.get(key, default)

        # 测试参数设置
        risk_manager = CustomRiskManager()

        # 设置基础风控参数
        risk_manager.max_position_ratio = 0.2
        risk_manager.stop_loss_rate = 0.03

        # 验证参数设置成功
        assert risk_manager.max_position_ratio == 0.2
        assert risk_manager.stop_loss_rate == 0.03

        # 设置自定义参数
        risk_manager.set_risk_param("max_drawdown", 0.15)
        risk_manager.set_risk_param("min_liquidity", 1000000)

        # 验证自定义参数
        assert risk_manager.get_risk_param("max_drawdown") == 0.15
        assert risk_manager.get_risk_param("min_liquidity") == 1000000
        assert risk_manager.get_risk_param("nonexistent", "default") == "default"

    def test_configuration_validation(self):
        """测试配置验证"""
        # 创建支持配置的风控管理器
        class ConfigurableRiskManager(BaseRiskManagement):
            def __init__(self, **kwargs):
                super().__init__(name="ConfigurableRisk", **kwargs)
                self.config = {
                    "max_position_ratio": 0.1,
                    "stop_loss_rate": 0.05,
                    "enabled": True
                }

            def validate_config(self):
                """验证配置的完整性"""
                errors = []

                # 验证必需的配置项
                if "max_position_ratio" not in self.config:
                    errors.append("Missing max_position_ratio")
                if "stop_loss_rate" not in self.config:
                    errors.append("Missing stop_loss_rate")

                # 验证配置值范围
                if self.config.get("max_position_ratio", 0) <= 0:
                    errors.append("max_position_ratio must be > 0")
                if self.config.get("max_position_ratio", 0) > 1:
                    errors.append("max_position_ratio must be <= 1")
                if self.config.get("stop_loss_rate", 0) <= 0:
                    errors.append("stop_loss_rate must be > 0")

                return errors

        # 测试有效配置
        risk_manager = ConfigurableRiskManager()
        errors = risk_manager.validate_config()
        assert len(errors) == 0  # 默认配置应该有效

        # 测试无效配置
        risk_manager.config["max_position_ratio"] = -0.1
        errors = risk_manager.validate_config()
        assert len(errors) > 0
        assert any("max_position_ratio must be > 0" in error for error in errors)

        # 测试缺失配置
        del risk_manager.config["stop_loss_rate"]
        errors = risk_manager.validate_config()
        assert len(errors) > 0
        assert any("Missing stop_loss_rate" in error for error in errors)

    def test_settings_persistence(self):
        """测试设置持久化"""
        risk_manager = BaseRiskManagement(name="PersistenceTest")

        # 创建带有持久化功能的数据接口
        class PersistentFeeder:
            def __init__(self):
                self.settings = {}
                self.connection_count = 0

            def save_setting(self, key, value):
                self.settings[key] = value

            def load_setting(self, key, default=None):
                return self.settings.get(key, default)

            def connect(self):
                self.connection_count += 1
                return f"connection_{self.connection_count}"

        # 测试设置持久化
        feeder = PersistentFeeder()
        risk_manager.bind_data_feeder(feeder)

        # 通过数据接口保存设置
        feeder.save_setting("risk_level", "high")
        feeder.save_setting("update_frequency", 60)

        # 验证设置持久化
        assert feeder.load_setting("risk_level") == "high"
        assert feeder.load_setting("update_frequency") == 60
        assert feeder.load_setting("nonexistent", "default") == "default"

        # 测试连接状态持久化
        conn1 = feeder.connect()
        assert conn1 == "connection_1"
        assert feeder.connection_count == 1

        # 重绑定后设置应该保持
        new_feeder = PersistentFeeder()
        risk_manager.bind_data_feeder(new_feeder)

        # 新接口应该是干净的
        assert new_feeder.load_setting("risk_level") is None
        assert new_feeder.connection_count == 0

        # 但原接口的设置仍然存在
        assert feeder.load_setting("risk_level") == "high"
        assert feeder.connection_count == 1


@pytest.mark.unit
class TestBaseRiskManagementOrderProcessing:
    """4. 订单处理测试"""

    def test_cal_method_interface(self):
        """测试cal方法接口"""
        risk_manager = BaseRiskManagement(name="InterfaceTest")

        # 验证cal方法存在且可调用
        assert hasattr(risk_manager, 'cal')
        assert callable(risk_manager.cal)

        # 创建测试参数
        portfolio_info = {'uuid': 'test_portfolio', 'cash': 100000}
        order = Order(portfolio_id='test_portfolio',
                     engine_id='test_engine',
                     run_id='test_run',
                     code="000001.SZ",
                     direction=DIRECTION_TYPES.LONG,
                     order_type=ORDER_TYPES.LIMITORDER,
                     status=ORDERSTATUS_TYPES.NEW,
                     volume=100,
                     limit_price=10.0)

        # 测试cal方法调用（基类应该直接返回原订单）
        result = risk_manager.cal(portfolio_info, order)

        # 验证返回的是Order对象
        assert isinstance(result, Order)
        assert result is order  # 基类返回同一个对象

    def test_order_passthrough(self):
        """测试订单直通"""
        risk_manager = BaseRiskManagement()

        # 创建测试订单
        portfolio_info = {'uuid': 'test', 'cash': 50000}
        original_order = Order(portfolio_id='test_portfolio',
                              engine_id='test_engine',
                              run_id='test_run',
                              code="000001.SZ",
                              direction=DIRECTION_TYPES.LONG,
                              order_type=ORDER_TYPES.LIMITORDER,
                              status=ORDERSTATUS_TYPES.NEW,
                              volume=200,
                              limit_price=15.0)

        # 调用cal方法
        processed_order = risk_manager.cal(portfolio_info, original_order)

        # 验证订单直通（未修改）
        assert processed_order is original_order  # 同一个对象
        assert processed_order.code == "000001.SZ"
        assert processed_order.direction == DIRECTION_TYPES.LONG
        assert processed_order.volume == 200
        assert processed_order.limit_price == 15.0
        assert processed_order.order_type == ORDER_TYPES.LIMITORDER
        assert processed_order.status == ORDERSTATUS_TYPES.NEW

    def test_order_modification(self):
        """测试订单修改"""
        # 创建一个会修改订单的自定义风控管理器
        class VolumeLimitRiskManager(BaseRiskManagement):
            def __init__(self, max_volume=100, **kwargs):
                super().__init__(name="VolumeLimitRisk", **kwargs)
                self.max_volume = max_volume

            def cal(self, portfolio_info, order):
                # 如果订单量超过限制，调整到最大允许量
                if order.volume > self.max_volume:
                    # 创建新的订单对象（模拟修改）
                    modified_order = Order(
                        portfolio_id=order.portfolio_id,
                        engine_id=order.engine_id,
                        run_id=order.run_id,
                        code=order.code,
                        direction=order.direction,
                        order_type=order.order_type,
                        status=order.status,
                        volume=self.max_volume,
                        limit_price=order.limit_price
                    )
                    return modified_order
                return order

        # 测试订单修改
        risk_manager = VolumeLimitRiskManager(max_volume=150)
        portfolio_info = {'uuid': 'test', 'cash': 100000}
        large_order = Order(portfolio_id='test_portfolio',
                           engine_id='test_engine',
                           run_id='test_run',
                           code="000001.SZ",
                           direction=DIRECTION_TYPES.LONG,
                           order_type=ORDER_TYPES.LIMITORDER,
                           status=ORDERSTATUS_TYPES.NEW,
                           volume=300,  # 超过限制
                           limit_price=20.0)

        # 处理订单
        processed_order = risk_manager.cal(portfolio_info, large_order)

        # 验证订单被修改
        assert processed_order is not large_order  # 返回了新对象
        assert processed_order.volume == 150  # 被调整到最大限制
        assert processed_order.code == "000001.SZ"  # 其他属性保持不变
        assert processed_order.limit_price == 20.0

        # 测试不需要修改的情况
        small_order = Order(portfolio_id='test_portfolio',
                           engine_id='test_engine',
                           run_id='test_run',
                           code="000002.SZ",
                           direction=DIRECTION_TYPES.LONG,
                           order_type=ORDER_TYPES.LIMITORDER,
                           status=ORDERSTATUS_TYPES.NEW,
                           volume=100,  # 未超过限制
                           limit_price=25.0)

        processed_small = risk_manager.cal(portfolio_info, small_order)
        assert processed_small is small_order  # 返回原对象

    def test_order_rejection(self):
        """测试订单拒绝"""
        # 创建一个会拒绝订单的自定义风控管理器
        class CashLimitRiskManager(BaseRiskManagement):
            def __init__(self, min_cash=10000, **kwargs):
                super().__init__(name="CashLimitRisk", **kwargs)
                self.min_cash = min_cash

            def cal(self, portfolio_info, order):
                # 如果现金不足，拒绝订单（返回None）
                cash = portfolio_info.get('cash', 0)
                required_cash = order.volume * order.limit_price

                if cash < self.min_cash or cash < required_cash:
                    return None  # 拒绝订单

                return order

        # 测试订单拒绝
        risk_manager = CashLimitRiskManager(min_cash=50000)

        # 现金不足的情况
        portfolio_info_low_cash = {'uuid': 'test', 'cash': 5000}
        order = Order(portfolio_id='test_portfolio',
                     engine_id='test_engine',
                     run_id='test_run',
                     code="000001.SZ",
                     direction=DIRECTION_TYPES.LONG,
                     order_type=ORDER_TYPES.LIMITORDER,
                     status=ORDERSTATUS_TYPES.NEW,
                     volume=1000,
                     limit_price=50.0)

        # 处理订单
        processed_order = risk_manager.cal(portfolio_info_low_cash, order)

        # 验证订单被拒绝
        assert processed_order is None

        # 测试订单被接受的情况
        portfolio_info_high_cash = {'uuid': 'test', 'cash': 100000}
        processed_order2 = risk_manager.cal(portfolio_info_high_cash, order)

        # 验证订单被接受
        assert processed_order2 is order

    def test_order_volume_adjustment(self):
        """测试订单量调整"""
        # 创建一个基于仓位比例调整订单量的风控管理器
        class PositionRatioRiskManager(BaseRiskManagement):
            def __init__(self, max_ratio=0.1, **kwargs):
                super().__init__(name="PositionRatioRisk", **kwargs)
                self.max_ratio = max_ratio

            def cal(self, portfolio_info, order):
                total_value = portfolio_info.get('total_value', 100000)
                max_position_value = total_value * self.max_ratio
                order_value = order.volume * order.limit_price

                if order_value > max_position_value:
                    # 调整订单量到最大允许值
                    adjusted_volume = int(float(max_position_value) / float(order.limit_price))
                    adjusted_order = Order(
                        portfolio_id=order.portfolio_id,
                        engine_id=order.engine_id,
                        run_id=order.run_id,
                        code=order.code,
                        direction=order.direction,
                        order_type=order.order_type,
                        status=order.status,
                        volume=adjusted_volume,
                        limit_price=order.limit_price
                    )
                    return adjusted_order

                return order

        # 测试订单量调整
        risk_manager = PositionRatioRiskManager(max_ratio=0.2)
        portfolio_info = {'uuid': 'test', 'total_value': 100000}
        large_order = Order(portfolio_id='test_portfolio',
                           engine_id='test_engine',
                           run_id='test_run',
                           code="000001.SZ",
                           direction=DIRECTION_TYPES.LONG,
                           order_type=ORDER_TYPES.LIMITORDER,
                           status=ORDERSTATUS_TYPES.NEW,
                           volume=3000,
                           limit_price=10.0)  # 订单价值30000，超过20%限制20000

        # 处理订单
        processed_order = risk_manager.cal(portfolio_info, large_order)

        # 验证订单量被调整
        assert processed_order is not large_order
        assert processed_order.volume == 2000  # 调整到20000/10=2000
        assert processed_order.limit_price == 10.0

    def test_portfolio_info_usage(self):
        """测试组合信息使用"""
        # 创建一个依赖组合信息的智能风控管理器
        class SmartRiskManager(BaseRiskManagement):
            def __init__(self, **kwargs):
                super().__init__(name="SmartRisk", **kwargs)
                self.last_portfolio_info = None

            def cal(self, portfolio_info, order):
                # 记录最后一次处理的组合信息
                self.last_portfolio_info = portfolio_info

                # 根据组合信息调整订单
                cash = portfolio_info.get('cash', 0)
                positions = portfolio_info.get('positions', {})

                # 如果没有现金，拒绝买单
                if order.direction == DIRECTION_TYPES.LONG and cash <= 0:
                    return None

                # 如果已持仓该股票，减少新订单量
                current_position = positions.get(order.code, 0)
                if current_position > 0:
                    adjusted_volume = max(order.volume // 2, 1)
                    order.volume = adjusted_volume

                return order

        # 测试组合信息使用
        risk_manager = SmartRiskManager()

        # 测试场景1：无现金，买单被拒绝
        portfolio_info_no_cash = {
            'uuid': 'test',
            'cash': 0,
            'positions': {}
        }
        buy_order = Order(portfolio_id='test_portfolio',
                         engine_id='test_engine',
                         run_id='test_run',
                         code="000001.SZ",
                         direction=DIRECTION_TYPES.LONG,
                         order_type=ORDER_TYPES.LIMITORDER,
                         status=ORDERSTATUS_TYPES.NEW,
                         volume=100,
                         limit_price=10.0)

        result1 = risk_manager.cal(portfolio_info_no_cash, buy_order)
        assert result1 is None
        assert risk_manager.last_portfolio_info == portfolio_info_no_cash

        # 测试场景2：有现金，有持仓，订单量被调整
        portfolio_info_with_position = {
            'uuid': 'test',
            'cash': 50000,
            'positions': {'000001.SZ': 500}
        }

        result2 = risk_manager.cal(portfolio_info_with_position, buy_order)
        assert result2 is buy_order
        assert result2.volume == 50  # 100//2 = 50

    def test_risk_threshold_validation(self):
        """测试风险阈值验证"""
        # 创建一个基于风险阈值的风控管理器
        class ThresholdRiskManager(BaseRiskManagement):
            def __init__(self, **kwargs):
                super().__init__(name="ThresholdRisk", **kwargs)
                self.max_single_order = 100000  # 单笔订单最大金额
                self.max_daily_loss = 50000     # 日最大亏损
                self.daily_loss = 0             # 当日已亏损

            def cal(self, portfolio_info, order):
                order_value = order.volume * order.limit_price

                # 检查单笔订单金额阈值
                if order_value > self.max_single_order:
                    return None

                # 检查日累计亏损阈值
                if self.daily_loss >= self.max_daily_loss:
                    return None

                # 检查单只股票持仓集中度
                total_value = portfolio_info.get('total_value', 100000)
                current_positions = portfolio_info.get('positions', {})
                current_position_value = float(current_positions.get(order.code, 0)) * 10.0  # 假设价格10.0
                new_position_value = float(current_position_value) + float(order_value)

                if new_position_value > total_value * 0.3:  # 单股不超过30%
                    # 调整订单量
                    max_allowed_value = total_value * 0.3 - current_position_value
                    if max_allowed_value > 0:
                        adjusted_volume = int(float(max_allowed_value) / float(order.limit_price))
                        order.volume = adjusted_volume
                    else:
                        return None

                return order

        # 测试风险阈值验证
        risk_manager = ThresholdRiskManager()
        portfolio_info = {
            'uuid': 'test',
            'total_value': 200000,
            'positions': {'000001.SZ': 1000}  # 已持仓1000股
        }

        # 测试场景1：单笔订单金额超限
        large_order = Order(portfolio_id='test_portfolio',
                           engine_id='test_engine',
                           run_id='test_run',
                           code="000002.SZ",
                           direction=DIRECTION_TYPES.LONG,
                           order_type=ORDER_TYPES.LIMITORDER,
                           status=ORDERSTATUS_TYPES.NEW,
                           volume=20000,
                           limit_price=10.0)  # 价值200000，超过100000限制

        result1 = risk_manager.cal(portfolio_info, large_order)
        assert result1 is None

        # 测试场景2：持仓集中度超限，订单被调整
        concentrated_order = Order(portfolio_id='test_portfolio',
                                 engine_id='test_engine',
                                 run_id='test_run',
                                 code="000001.SZ",  # 已持仓的股票
                                 direction=DIRECTION_TYPES.LONG,
                                 order_type=ORDER_TYPES.LIMITORDER,
                                 status=ORDERSTATUS_TYPES.NEW,
                                 volume=5000,
                                 limit_price=10.0)  # 价值50000

        result2 = risk_manager.cal(portfolio_info, concentrated_order)
        assert result2 is concentrated_order
        assert result2.volume <= 5000  # 可能被调整或保持不变

    def test_order_processing_consistency(self):
        """测试订单处理一致性"""
        # 创建一个确定性的风控管理器
        class DeterministicRiskManager(BaseRiskManagement):
            def __init__(self, **kwargs):
                super().__init__(name="DeterministicRisk", **kwargs)
                self.processing_count = 0

            def cal(self, portfolio_info, order):
                self.processing_count += 1

                # 基于订单代码的确定性处理
                if '1' in order.code:  # 包含1的股票代码
                    if order.volume > 100:
                        # 调整到100
                        order.volume = 100
                elif '2' in order.code:  # 包含2的股票代码
                    if order.limit_price > 50:
                        # 拒绝高价订单
                        return None

                return order

        # 测试处理一致性
        risk_manager = DeterministicRiskManager()
        portfolio_info = {'uuid': 'test', 'cash': 100000}

        # 创建相同的订单多次处理
        order1 = Order(portfolio_id='test_portfolio',
                      engine_id='test_engine',
                      run_id='test_run',
                      code="000001.SZ",
                      direction=DIRECTION_TYPES.LONG,
                      order_type=ORDER_TYPES.LIMITORDER,
                      status=ORDERSTATUS_TYPES.NEW,
                      volume=200,
                      limit_price=10.0)

        # 多次处理相同订单
        results = []
        for i in range(5):
            # 每次都创建新的订单对象（模拟不同的订单实例但参数相同）
            test_order = Order(portfolio_id='test_portfolio',
                              engine_id='test_engine',
                              run_id='test_run',
                              code="000001.SZ",
                              direction=DIRECTION_TYPES.LONG,
                              order_type=ORDER_TYPES.LIMITORDER,
                              status=ORDERSTATUS_TYPES.NEW,
                              volume=200,
                              limit_price=10.0)
            result = risk_manager.cal(portfolio_info, test_order)
            results.append(result.volume if result else None)

        # 验证处理结果一致性
        # 每次都创建新的订单对象，每个都会被调整到100
        assert all(volume == 100 for volume in results)  # 所有结果都是100
        assert risk_manager.processing_count == 5

        # 测试另一个订单的一致性
        order2 = Order(portfolio_id='test_portfolio',
                      engine_id='test_engine',
                      run_id='test_run',
                      code="000002.SZ",
                      direction=DIRECTION_TYPES.LONG,
                      order_type=ORDER_TYPES.LIMITORDER,
                      status=ORDERSTATUS_TYPES.NEW,
                      volume=100,
                      limit_price=60.0)  # 高于50，应该被拒绝

        results2 = []
        for i in range(3):
            test_order = Order(portfolio_id='test_portfolio',
                              engine_id='test_engine',
                              run_id='test_run',
                              code="000002.SZ",
                              direction=DIRECTION_TYPES.LONG,
                              order_type=ORDER_TYPES.LIMITORDER,
                              status=ORDERSTATUS_TYPES.NEW,
                              volume=100,
                              limit_price=60.0)
            result = risk_manager.cal(portfolio_info, test_order)
            results2.append(result)

        # 验证所有都被拒绝
        assert all(result is None for result in results2)
        assert risk_manager.processing_count == 8


@pytest.mark.unit
class TestBaseRiskManagementSignalGeneration:
    """5. 风控信号生成测试"""

    def test_generate_signals_method_interface(self):
        """测试generate_signals方法接口"""
        risk_manager = BaseRiskManagement(name="InterfaceTest")

        # 验证generate_signals方法存在且可调用
        assert hasattr(risk_manager, 'generate_signals')
        assert callable(risk_manager.generate_signals)

        # 创建测试参数
        portfolio_info = {'uuid': 'test_portfolio', 'cash': 100000}
        from ginkgo.trading.events.base_event import EventBase
        event = EventBase()

        # 测试generate_signals方法调用（基类应该返回空列表）
        result = risk_manager.generate_signals(portfolio_info, event)

        # 验证返回的是列表类型
        assert isinstance(result, list)
        assert result == []  # 基类返回空列表

    def test_empty_signal_generation(self):
        """测试空信号生成"""
        risk_manager = BaseRiskManagement()

        # 测试不同类型的portfolio_info都返回空列表
        portfolio_infos = [
            {},  # 空字典
            {'uuid': 'test_portfolio'},  # 简单字典
            {'cash': 100000, 'positions': {}},  # 包含现金和持仓信息
            {'uuid': 'test', 'cash': 50000, 'now': datetime.now()}  # 完整信息
        ]

        # 创建不同类型的测试事件
        from ginkgo.trading.events.base_event import EventBase
        events = [EventBase() for _ in range(4)]

        # 验证所有组合都返回空列表
        for portfolio_info, event in zip(portfolio_infos, events):
            result = risk_manager.generate_signals(portfolio_info, event)
            assert isinstance(result, list)
            assert len(result) == 0
            assert result == []

    def test_stop_loss_signal_generation(self):
        """测试止损信号生成"""
        # 创建一个会生成止损信号的风控管理器
        class StopLossRiskManager(BaseRiskManagement):
            def __init__(self, loss_threshold=0.1, **kwargs):
                super().__init__(name="StopLossRisk", **kwargs)
                self.loss_threshold = loss_threshold

            def generate_signals(self, portfolio_info, event):
                signals = []
                positions = portfolio_info.get('positions', {})

                # 检查每个持仓的亏损情况
                for code, position_data in positions.items():
                    if isinstance(position_data, dict):
                        current_price = position_data.get('current_price', 0)
                        cost_price = position_data.get('cost_price', 0)
                        position_value = position_data.get('value', 0)

                        if cost_price > 0 and current_price > 0:
                            loss_rate = (cost_price - current_price) / cost_price

                            # 如果亏损超过阈值，生成卖出信号
                            if loss_rate >= self.loss_threshold:
                                signal = Signal(
                                    portfolio_id=portfolio_info.get('uuid', ''),
                                    engine_id=portfolio_info.get('engine_id', ''),
                                    run_id=portfolio_info.get('run_id', ''),
                                    timestamp=datetime.now(),
                                    code=code,
                                    direction=DIRECTION_TYPES.SHORT,  # 卖出
                                    reason=f"Stop Loss: {loss_rate:.2%} loss exceeds {self.loss_threshold:.2%}"
                                )
                                signals.append(signal)

                return signals

        # 测试止损信号生成
        risk_manager = StopLossRiskManager(loss_threshold=0.1)

        # 模拟有亏损持仓的投资组合
        portfolio_info = {
            'uuid': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'positions': {
                '000001.SZ': {
                    'current_price': 9.0,  # 当前价格
                    'cost_price': 10.0,     # 成本价格
                    'value': 9000           # 持仓价值
                },
                '000002.SZ': {
                    'current_price': 11.0,
                    'cost_price': 10.0,
                    'value': 11000
                },
                '000003.SZ': {
                    'current_price': 8.0,
                    'cost_price': 10.0,
                    'value': 8000
                }
            }
        }

        event = EventBase()
        signals = risk_manager.generate_signals(portfolio_info, event)

        # 验证生成了正确的止损信号
        assert len(signals) == 2  # 000001和000003都亏损超过10%
        assert all(isinstance(signal, Signal) for signal in signals)
        assert all(signal.direction == DIRECTION_TYPES.SHORT for signal in signals)

        # 验证亏损超过阈值的股票生成了信号
        loss_codes = [signal.code for signal in signals]
        assert '000001.SZ' in loss_codes  # 10%亏损
        assert '000003.SZ' in loss_codes  # 20%亏损
        assert '000002.SZ' not in loss_codes  # 盈利，无信号

    def test_take_profit_signal_generation(self):
        """测试止盈信号生成"""
        # 创建一个会生成止盈信号的风控管理器
        class TakeProfitRiskManager(BaseRiskManagement):
            def __init__(self, profit_threshold=0.2, **kwargs):
                super().__init__(name="TakeProfitRisk", **kwargs)
                self.profit_threshold = profit_threshold

            def generate_signals(self, portfolio_info, event):
                signals = []
                positions = portfolio_info.get('positions', {})

                # 检查每个持仓的盈利情况
                for code, position_data in positions.items():
                    if isinstance(position_data, dict):
                        current_price = position_data.get('current_price', 0)
                        cost_price = position_data.get('cost_price', 0)
                        position_value = position_data.get('value', 0)

                        if cost_price > 0 and current_price > 0:
                            profit_rate = (current_price - cost_price) / cost_price

                            # 如果盈利超过阈值，生成卖出信号
                            if profit_rate >= self.profit_threshold:
                                signal = Signal(
                                    portfolio_id=portfolio_info.get('uuid', ''),
                                    engine_id=portfolio_info.get('engine_id', ''),
                                    run_id=portfolio_info.get('run_id', ''),
                                    timestamp=datetime.now(),
                                    code=code,
                                    direction=DIRECTION_TYPES.SHORT,  # 卖出止盈
                                    reason=f"Take Profit: {profit_rate:.2%} profit exceeds {self.profit_threshold:.2%}"
                                )
                                signals.append(signal)

                return signals

        # 测试止盈信号生成
        risk_manager = TakeProfitRiskManager(profit_threshold=0.2)

        # 模拟有盈利持仓的投资组合
        portfolio_info = {
            'uuid': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'positions': {
                '000001.SZ': {
                    'current_price': 12.0,  # 当前价格
                    'cost_price': 10.0,     # 成本价格
                    'value': 12000          # 持仓价值
                },
                '000002.SZ': {
                    'current_price': 11.0,
                    'cost_price': 10.0,
                    'value': 11000
                },
                '000003.SZ': {
                    'current_price': 9.0,
                    'cost_price': 10.0,
                    'value': 9000
                }
            }
        }

        event = EventBase()
        signals = risk_manager.generate_signals(portfolio_info, event)

        # 验证生成了正确的止盈信号
        assert len(signals) == 1  # 只有000001盈利超过20%
        assert isinstance(signals[0], Signal)
        assert signals[0].direction == DIRECTION_TYPES.SHORT
        assert signals[0].code == '000001.SZ'

        # 验证盈利超过阈值的股票生成了信号
        profit_codes = [signal.code for signal in signals]
        assert '000001.SZ' in profit_codes  # 20%盈利
        assert '000002.SZ' not in profit_codes  # 10%盈利，未达到阈值
        assert '000003.SZ' not in profit_codes  # 亏损，无信号

    def test_position_control_signal(self):
        """测试仓位控制信号"""
        # 创建仓位控制风控管理器
        class PositionControlRiskManager(BaseRiskManagement):
            def __init__(self, max_position_ratio=0.3, **kwargs):
                super().__init__(name="PositionControlRisk", **kwargs)
                self.max_position_ratio = max_position_ratio

            def generate_signals(self, portfolio_info, event):
                signals = []
                positions = portfolio_info.get('positions', {})
                total_value = portfolio_info.get('total_value', 100000)

                # 检查单个持仓是否超过限制
                for code, position_data in positions.items():
                    if isinstance(position_data, dict):
                        position_value = position_data.get('value', 0)
                        current_ratio = position_value / total_value if total_value > 0 else 0

                        # 如果持仓比例超过限制，生成减仓信号
                        if current_ratio > self.max_position_ratio:
                            # 计算需要卖出的比例
                            sell_ratio = (current_ratio - self.max_position_ratio) / current_ratio

                            signal = Signal(
                                portfolio_id=portfolio_info.get('uuid', ''),
                                engine_id=portfolio_info.get('engine_id', ''),
                                run_id=portfolio_info.get('run_id', ''),
                                timestamp=datetime.now(),
                                code=code,
                                direction=DIRECTION_TYPES.SHORT,
                                reason=f"Position Control: {current_ratio:.1%} exceeds {self.max_position_ratio:.1%}"
                            )
                            signals.append(signal)

                return signals

        # 测试仓位控制信号
        risk_manager = PositionControlRiskManager(max_position_ratio=0.3)

        portfolio_info = {
            'uuid': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'total_value': 100000,
            'positions': {
                '000001.SZ': {'value': 50000},  # 50%，超过30%限制
                '000002.SZ': {'value': 20000},  # 20%，在限制内
                '000003.SZ': {'value': 35000}   # 35%，超过30%限制
            }
        }

        event = EventBase()
        signals = risk_manager.generate_signals(portfolio_info, event)

        # 验证生成了仓位控制信号
        assert len(signals) == 2  # 000001和000003都超限
        assert all(signal.direction == DIRECTION_TYPES.SHORT for signal in signals)

        control_codes = [signal.code for signal in signals]
        assert '000001.SZ' in control_codes
        assert '000003.SZ' in control_codes
        assert '000002.SZ' not in control_codes

    def test_market_risk_signal(self):
        """测试市场风险信号"""
        # 创建市场风险风控管理器
        class MarketRiskManager(BaseRiskManagement):
            def __init__(self, market_drop_threshold=0.05, **kwargs):
                super().__init__(name="MarketRisk", **kwargs)
                self.market_drop_threshold = market_drop_threshold

            def generate_signals(self, portfolio_info, event):
                signals = []

                # 模拟市场暴跌事件
                if hasattr(event, 'market_drop') and event.market_drop >= self.market_drop_threshold:
                    # 清仓所有持仓
                    positions = portfolio_info.get('positions', {})
                    for code in positions.keys():
                        signal = Signal(
                            portfolio_id=portfolio_info.get('uuid', ''),
                            engine_id=portfolio_info.get('engine_id', ''),
                            run_id=portfolio_info.get('run_id', ''),
                            timestamp=datetime.now(),
                            code=code,
                            direction=DIRECTION_TYPES.SHORT,
                            reason=f"Market Risk: Market dropped {event.market_drop:.1%}"
                        )
                        signals.append(signal)

                return signals

        # 测试市场风险信号
        risk_manager = MarketRiskManager(market_drop_threshold=0.05)

        # 创建市场暴跌事件
        class MarketDropEvent:
            def __init__(self, drop_rate):
                self.market_drop = drop_rate

        portfolio_info = {
            'uuid': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'positions': {'000001.SZ': {}, '000002.SZ': {}, '000003.SZ': {}}
        }

        # 测试市场暴跌事件
        drop_event = MarketDropEvent(0.08)  # 市场下跌8%
        signals = risk_manager.generate_signals(portfolio_info, drop_event)

        # 验证生成了清仓信号
        assert len(signals) == 3
        assert all(signal.direction == DIRECTION_TYPES.SHORT for signal in signals)

        signal_codes = [signal.code for signal in signals]
        assert set(signal_codes) == {'000001.SZ', '000002.SZ', '000003.SZ'}

        # 测试正常市场情况（无信号）
        normal_event = MarketDropEvent(0.02)  # 市场下跌2%
        normal_signals = risk_manager.generate_signals(portfolio_info, normal_event)
        assert len(normal_signals) == 0

    def test_multiple_signals_coordination(self):
        """测试多信号协调"""
        # 创建综合风控管理器
        class ComprehensiveRiskManager(BaseRiskManagement):
            def __init__(self, **kwargs):
                super().__init__(name="ComprehensiveRisk", **kwargs)
                self.stop_loss_threshold = 0.1
                self.profit_threshold = 0.3

            def generate_signals(self, portfolio_info, event):
                signals = []
                positions = portfolio_info.get('positions', {})

                for code, position_data in positions.items():
                    if isinstance(position_data, dict):
                        current_price = position_data.get('current_price', 0)
                        cost_price = position_data.get('cost_price', 0)

                        if cost_price > 0 and current_price > 0:
                            change_rate = (current_price - cost_price) / cost_price

                            # 亏损超过阈值，生成止损信号
                            if change_rate <= -self.stop_loss_threshold:
                                signal = Signal(
                                    portfolio_id=portfolio_info.get('uuid', ''),
                                    engine_id=portfolio_info.get('engine_id', ''),
                                    run_id=portfolio_info.get('run_id', ''),
                                    timestamp=datetime.now(),
                                    code=code,
                                    direction=DIRECTION_TYPES.SHORT,
                                    reason=f"Stop Loss: {abs(change_rate):.1%} loss"
                                )
                                signals.append(signal)

                            # 盈利超过阈值，生成止盈信号
                            elif change_rate >= self.profit_threshold:
                                signal = Signal(
                                    portfolio_id=portfolio_info.get('uuid', ''),
                                    engine_id=portfolio_info.get('engine_id', ''),
                                    run_id=portfolio_info.get('run_id', ''),
                                    timestamp=datetime.now(),
                                    code=code,
                                    direction=DIRECTION_TYPES.SHORT,
                                    reason=f"Take Profit: {change_rate:.1%} profit"
                                )
                                signals.append(signal)

                return signals

        # 测试多信号协调
        risk_manager = ComprehensiveRiskManager()

        portfolio_info = {
            'uuid': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'positions': {
                '000001.SZ': {'current_price': 8.0, 'cost_price': 10.0},  # 20%亏损，止损
                '000002.SZ': {'current_price': 13.0, 'cost_price': 10.0}, # 30%盈利，止盈
                '000003.SZ': {'current_price': 9.5, 'cost_price': 10.0},  # 5%亏损，无信号
            }
        }

        event = EventBase()
        signals = risk_manager.generate_signals(portfolio_info, event)

        # 验证生成了正确的多种信号
        assert len(signals) == 2

        # 验证信号原因和类型
        reasons = [signal.reason for signal in signals]
        assert any("Stop Loss" in reason for reason in reasons)
        assert any("Take Profit" in reason for reason in reasons)

    def test_signal_priority_handling(self):
        """测试信号优先级处理"""
        # 创建有优先级的风控管理器
        class PriorityRiskManager(BaseRiskManagement):
            def __init__(self, **kwargs):
                super().__init__(name="PriorityRisk", **kwargs)
                self.emergency_threshold = 0.2  # 紧急止损阈值
                self.normal_threshold = 0.1     # 普通止损阈值

            def generate_signals(self, portfolio_info, event):
                signals = []
                positions = portfolio_info.get('positions', {})

                for code, position_data in positions.items():
                    if isinstance(position_data, dict):
                        current_price = position_data.get('current_price', 0)
                        cost_price = position_data.get('cost_price', 0)

                        if cost_price > 0 and current_price > 0:
                            loss_rate = (cost_price - current_price) / cost_price

                            # 紧急止损（优先级最高）
                            if loss_rate >= self.emergency_threshold:
                                signal = Signal(
                                    portfolio_id=portfolio_info.get('uuid', ''),
                                    engine_id=portfolio_info.get('engine_id', ''),
                                    run_id=portfolio_info.get('run_id', ''),
                                    timestamp=datetime.now(),
                                    code=code,
                                    direction=DIRECTION_TYPES.SHORT,
                                    reason=f"EMERGENCY Stop Loss: {loss_rate:.1%}"
                                )
                                signals.append(signal)

                            # 普通止损（优先级较低）
                            elif loss_rate >= self.normal_threshold:
                                signal = Signal(
                                    portfolio_id=portfolio_info.get('uuid', ''),
                                    engine_id=portfolio_info.get('engine_id', ''),
                                    run_id=portfolio_info.get('run_id', ''),
                                    timestamp=datetime.now(),
                                    code=code,
                                    direction=DIRECTION_TYPES.SHORT,
                                    reason=f"Stop Loss: {loss_rate:.1%}"
                                )
                                signals.append(signal)

                # 按优先级排序：紧急信号在前
                signals.sort(key=lambda s: 0 if "EMERGENCY" in s.reason else 1)
                return signals

        # 测试信号优先级
        risk_manager = PriorityRiskManager()

        portfolio_info = {
            'uuid': 'test_portfolio',
            'engine_id': 'test_engine',
            'run_id': 'test_run',
            'positions': {
                '000001.SZ': {'current_price': 7.0, 'cost_price': 10.0},  # 30%亏损，紧急
                '000002.SZ': {'current_price': 8.5, 'cost_price': 10.0},  # 15%亏损，普通
            }
        }

        event = EventBase()
        signals = risk_manager.generate_signals(portfolio_info, event)

        # 验证信号优先级排序
        assert len(signals) == 2
        assert "EMERGENCY" in signals[0].reason  # 紧急信号在前
        assert "EMERGENCY" not in signals[1].reason
        assert signals[0].code == '000001.SZ'
        assert signals[1].code == '000002.SZ'


@pytest.mark.unit
class TestBaseRiskManagementPortfolioAnalysis:
    """6. 投资组合风险分析测试"""

    def test_portfolio_info_parsing(self):
        """测试组合信息解析"""
        # TODO: 测试对portfolio_info参数的正确解析
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_position_risk_calculation(self):
        """测试持仓风险计算"""
        # TODO: 测试单个持仓和总体持仓的风险计算
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_capital_utilization_analysis(self):
        """测试资金使用率分析"""
        # TODO: 测试可用资金和已用资金的分析
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_concentration_risk_assessment(self):
        """测试集中度风险评估"""
        # TODO: 测试投资组合的集中度风险检查
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_correlation_risk_analysis(self):
        """测试相关性风险分析"""
        # TODO: 测试持仓资产间的相关性风险分析
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_liquidity_risk_assessment(self):
        """测试流动性风险评估"""
        # TODO: 测试持仓资产的流动性风险评估
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_dynamic_risk_monitoring(self):
        """测试动态风险监控"""
        # TODO: 测试随市场变化的实时风险监控
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_portfolio_risk_metrics(self):
        """测试组合风险指标"""
        # TODO: 测试各种投资组合风险指标的计算
        assert False, "TDD Red阶段：测试用例尚未实现"


@pytest.mark.unit
class TestBaseRiskManagementEventDriven:
    """7. 事件驱动风控测试"""

    def test_event_type_identification(self):
        """测试事件类型识别"""
        # TODO: 测试对不同类型事件的正确识别和分类
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_price_event_response(self):
        """测试价格事件响应"""
        # TODO: 测试对价格更新事件的风控响应
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_market_anomaly_response(self):
        """测试市场异常事件响应"""
        # TODO: 测试对市场异常事件（如暴跌）的应急响应
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_trading_time_event_handling(self):
        """测试交易时间事件处理"""
        # TODO: 测试对开盘、收盘等时间事件的处理
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_risk_threshold_trigger(self):
        """测试风控阈值触发"""
        # TODO: 测试各种风控阈值被触发时的事件处理
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_event_priority_processing(self):
        """测试事件优先级处理"""
        # TODO: 测试多个事件同时到达时的优先级处理
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_event_state_management(self):
        """测试事件状态管理"""
        # TODO: 测试风控事件的状态跟踪和管理
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_event_chain_reaction(self):
        """测试事件链式反应"""
        # TODO: 测试一个风控事件触发其他事件的链式反应
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_event_performance_monitoring(self):
        """测试事件性能监控"""
        # TODO: 测试事件处理的性能监控和优化
        assert False, "TDD Red阶段：测试用例尚未实现"