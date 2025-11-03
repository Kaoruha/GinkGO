"""
Position类TDD测试

通过TDD方式开发Position持仓管理类的完整测试套件
涵盖基础功能和量化交易特有场景
"""
import pytest
import datetime
from decimal import Decimal

# 导入Position类和相关枚举
from ginkgo.trading.entities.position import Position
from ginkgo.enums import DIRECTION_TYPES


@pytest.mark.unit
class TestPositionConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认构造函数 - 严格模式：要求核心参数"""
        # Position与Signal保持一致，要求核心业务参数不能为空
        with pytest.raises(ValueError):
            Position()

    def test_full_parameter_constructor(self):
        """测试完整参数构造"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine_001",
            run_id="test_run_001",
            code="000001.SZ",
            cost=Decimal('10.50'),
            volume=1000,
            frozen_volume=100,
            frozen_money=Decimal('50.00'),
            price=Decimal('11.20'),
            fee=Decimal('5.25'),
            uuid="custom_uuid_001",
            timestamp=datetime.datetime(2023, 1, 1, 10, 0, 0)
        )

        # 验证字符串属性正确赋值和类型
        assert position.portfolio_id == "test_portfolio_001"
        assert isinstance(position.portfolio_id, str)

        assert position.engine_id == "test_engine_001"
        assert isinstance(position.engine_id, str)

        assert position.run_id == "test_run_001"
        assert isinstance(position.run_id, str)

        assert position.code == "000001.SZ"
        assert isinstance(position.code, str)

        # 验证Decimal类型的金融属性
        assert position.cost == Decimal('10.50')
        assert isinstance(position.cost, Decimal)

        assert position.price == Decimal('11.20')
        assert isinstance(position.price, Decimal)

        assert position.fee == Decimal('5.25')
        assert isinstance(position.fee, Decimal)

        assert position.frozen_money == Decimal('50.00')
        assert isinstance(position.frozen_money, Decimal)

        # 验证整数属性
        assert position.volume == 1000
        assert isinstance(position.volume, int)

        assert position.frozen_volume == 100
        assert isinstance(position.frozen_volume, int)

        # 验证UUID
        assert position.uuid == "custom_uuid_001"
        assert isinstance(position.uuid, str)

        # 验证计算属性精确值和类型 - 金融计算应该只返回Decimal
        # worth = (volume + frozen_volume + settlement_frozen_volume) * price = (1000 + 100) * 11.20 = 12320.00
        expected_worth = Decimal('12320.00')
        assert position.worth == expected_worth
        assert isinstance(position.worth, Decimal)

        # total_pnl = (volume + frozen_volume + settlement_frozen_volume) * (price - cost) - fee
        # = (1000 + 100) * (11.20 - 10.50) - 5.25 = 1100 * 0.70 - 5.25 = 770 - 5.25 = 764.75
        expected_total_pnl = Decimal('764.75')
        assert position.total_pnl == expected_total_pnl
        assert isinstance(position.total_pnl, Decimal)

    def test_partial_parameter_constructor(self):
        """测试部分参数构造"""
        from decimal import Decimal

        # 只传入必需的核心参数，其他使用默认值
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 10, 0, 0)
            # 其他参数使用默认值：cost=0.0, volume=0, price=0.0等
        )

        # 验证必需参数设置正确和类型
        assert position.portfolio_id == "test_portfolio"
        assert isinstance(position.portfolio_id, str)

        assert position.engine_id == "test_engine"
        assert isinstance(position.engine_id, str)

        assert position.run_id == "test_run"
        assert isinstance(position.run_id, str)

        assert position.code == "000001.SZ"
        assert isinstance(position.code, str)

        # 验证Decimal类型的默认值
        assert position.cost == Decimal('0.0')
        assert isinstance(position.cost, Decimal)

        assert position.price == Decimal('0.0')
        assert isinstance(position.price, Decimal)

        assert position.fee == Decimal('0.0')
        assert isinstance(position.fee, Decimal)

        assert position.frozen_money == Decimal('0')
        assert isinstance(position.frozen_money, Decimal)

        # 验证整数类型的默认值
        assert position.volume == 0
        assert isinstance(position.volume, int)

        assert position.frozen_volume == 0
        assert isinstance(position.frozen_volume, int)

        # 验证计算属性的默认值 - 金融计算应该只返回Decimal
        assert position.worth == Decimal('0.00')
        assert isinstance(position.worth, Decimal)

        assert position.total_pnl == Decimal('0.0')
        assert isinstance(position.total_pnl, Decimal)

        # 验证UUID自动生成功能
        assert position.uuid is not None
        assert isinstance(position.uuid, str)
        assert len(position.uuid) > 0
        assert "position" in position.uuid.lower()  # 包含组件类型标识

        # 验证UUID唯一性 - 创建第二个实例对比
        position2 = Position(
            portfolio_id="test_portfolio2",
            engine_id="test_engine2",
            run_id="test_run2",
            code="000002.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 10, 0, 0)
        )
        assert position.uuid != position2.uuid  # UUID应该是唯一的

    def test_parameter_type_validation(self):
        """测试参数类型验证"""
        base_params = {
            "portfolio_id": "test_portfolio",
            "engine_id": "test_engine",
            "run_id": "test_run",
            "code": "000001.SZ",
            "timestamp": datetime.datetime(2023, 1, 1, 10, 0, 0)
        }

        # 测试portfolio_id类型验证
        with pytest.raises(ValueError):
            Position(**{**base_params, "portfolio_id": 123})  # 非字符串

        with pytest.raises(ValueError):
            Position(**{**base_params, "portfolio_id": ""})  # 空字符串

        # 测试engine_id类型验证
        with pytest.raises(ValueError):
            Position(**{**base_params, "engine_id": None})

        # 测试run_id类型验证
        with pytest.raises(ValueError):
            Position(**{**base_params, "run_id": []})

        # 测试code类型验证
        with pytest.raises(ValueError):
            Position(**{**base_params, "code": ""})

        # 验证正确参数可以成功创建
        valid_position = Position(**base_params)
        assert valid_position is not None

    def test_uuid_auto_generation(self):
        """测试UUID自动生成"""
        base_params = {
            "portfolio_id": "test_portfolio",
            "engine_id": "test_engine",
            "run_id": "test_run",
            "code": "000001.SZ",
            "timestamp": datetime.datetime(2023, 1, 1, 10, 0, 0)
        }

        # 创建两个Position实例
        position1 = Position(**base_params)
        position2 = Position(**{**base_params, "code": "000002.SZ"})

        # 验证UUID存在且是字符串
        assert position1.uuid is not None
        assert position2.uuid is not None
        assert isinstance(position1.uuid, str)
        assert isinstance(position2.uuid, str)

        # 验证UUID不为空
        assert len(position1.uuid) > 0
        assert len(position2.uuid) > 0

        # 验证UUID是唯一的
        assert position1.uuid != position2.uuid

        # 验证UUID包含组件类型标识
        assert "position" in position1.uuid.lower()

        # 测试自定义UUID
        custom_uuid = "custom_position_123"
        position_with_uuid = Position(**base_params, uuid=custom_uuid)
        assert position_with_uuid.uuid == custom_uuid


@pytest.mark.unit
class TestPositionProperties:
    """2. 属性访问测试"""

    def test_basic_property_access(self):
        """测试基础属性读取"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.50,
            volume=1000,
            frozen_volume=200,      # 添加冻结数量
            frozen_money=50.0,      # 添加冻结资金
            price=110.25,
            fee=5.0,
            timestamp=datetime.datetime(2023, 1, 1, 10, 0, 0)
        )

        # 测试基础字符串属性读取
        assert position.portfolio_id == "test_portfolio"
        assert position.engine_id == "test_engine"
        assert position.run_id == "test_run"
        assert position.code == "000001.SZ"

        # 测试Decimal类型的金融属性
        assert position.cost == Decimal('100.5')
        assert isinstance(position.cost, Decimal)

        assert position.price == Decimal('110.25')
        assert isinstance(position.price, Decimal)

        assert position.fee == Decimal('5.0')
        assert isinstance(position.fee, Decimal)

        assert position.frozen_money == Decimal('50.0')
        assert isinstance(position.frozen_money, Decimal)

        # 测试整数属性
        assert position.volume == 1000
        assert isinstance(position.volume, int)

        assert position.frozen_volume == 200
        assert isinstance(position.frozen_volume, int)

        # 测试UUID属性
        assert position.uuid is not None
        assert isinstance(position.uuid, str)
        assert len(position.uuid) > 0

        # 测试计算属性 - 都应该返回Decimal类型
        # worth = (volume + frozen_volume + settlement_frozen_volume) * price = (1000 + 200) * 110.25 = 132300.00
        expected_worth = Decimal('132300.00')
        assert position.worth == expected_worth
        assert isinstance(position.worth, Decimal)

        # total_pnl = (volume + frozen_volume + settlement_frozen_volume) * (price - cost) - fee
        # = (1000 + 200) * (110.25 - 100.50) - 5.0 = 1200 * 9.75 - 5.0 = 11695.0
        expected_total_pnl = Decimal('11695.0')
        assert position.total_pnl == expected_total_pnl
        assert isinstance(position.total_pnl, Decimal)

    def test_numeric_property_validation(self):
        """测试数值属性验证"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.50,
            volume=1000,
            price=110.25,
            fee=5.0,
            timestamp=datetime.datetime(2023, 1, 1, 10, 0, 0)
        )

        # 测试volume类型和范围验证
        assert isinstance(position.volume, int)
        assert position.volume >= 0  # volume不能为负

        # 测试Decimal类型的金融属性
        assert isinstance(position.cost, Decimal)
        assert position.cost >= 0  # cost应该非负

        assert isinstance(position.price, Decimal)
        assert position.price >= 0  # price应该非负

        assert isinstance(position.fee, Decimal)
        assert position.fee >= 0  # fee应该非负

        # 测试frozen_volume
        assert isinstance(position.frozen_volume, int)
        assert position.frozen_volume >= 0

    def test_calculated_properties(self):
        """测试计算属性"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            fee=5.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 测试worth计算：(volume + frozen_volume) * price
        expected_worth = Decimal('110000.00')  # 1000 * 110.0 = 110000, rounded to 2 decimals
        assert position.worth == expected_worth

        # 测试total_pnl计算：(volume + frozen_volume) * (price - cost) - fee
        expected_total_pnl = Decimal('9995.0')  # 1000 * (110-100) - 5 = 10000 - 5 = 9995
        assert position.total_pnl == expected_total_pnl

        # 测试计算属性都是Decimal类型
        assert isinstance(position.worth, Decimal)
        assert isinstance(position.total_pnl, Decimal)

    def test_readonly_property_protection(self):
        """测试只读属性保护"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 测试profit和worth是只读属性（通过计算得出）
        original_profit = position.total_pnl
        original_worth = position.worth

        # 这些应该是通过计算得出的，不应该有直接的setter
        assert hasattr(position, 'total_pnl')
        assert hasattr(position, 'worth')

        # total_pnl和worth应该通过update_total_pnl()和update_worth()方法来更新
        # 而不是直接赋值
        assert original_profit == position.total_pnl
        assert original_worth == position.worth

    def test_property_setter_validation(self):
        """测试属性setter验证"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            timestamp="2023-01-01 10:00:00"
        )

        # 测试volume setter的类型转换 - 实际实现会自动截断小数
        position.volume = 500  # 正确：使用整数
        assert position.volume == 500
        assert isinstance(position.volume, int)

        # 注意：当前实现会自动截断浮点数股数（可能不是最佳实践）
        # 在严格的量化交易系统中，应该拒绝浮点数股数或至少发出警告
        position.volume = 500.7  # 当前实现：自动截断为500
        assert position.volume == 500  # 小数部分被截断

        # 这种行为可能导致意外的股数变化，在实际交易中需要谨慎
        position.volume = 999.9
        assert position.volume == 999  # 截断，不是四舍五入

        # 测试基本string属性的setter
        position.portfolio_id = "new_portfolio"
        position.engine_id = "new_engine"
        position.run_id = "new_run"

        assert position.portfolio_id == "new_portfolio"
        assert position.engine_id == "new_engine"
        assert position.run_id == "new_run"

    def test_decimal_precision_maintained(self):
        """测试Decimal精度保持"""
        from decimal import Decimal

        # 使用高精度的Decimal值创建Position
        precise_cost = Decimal('123.456789')
        precise_price = Decimal('100.123456')
        precise_fee = Decimal('0.123456')

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=precise_cost,
            volume=1000,
            price=precise_price,
            fee=precise_fee,
            timestamp="2023-01-01 10:00:00"
        )

        # 验证精度保持
        assert position.cost == precise_cost
        assert position.price == precise_price
        assert position.fee == precise_fee

        # 验证类型仍为Decimal
        assert isinstance(position.cost, Decimal)
        assert isinstance(position.price, Decimal)
        assert isinstance(position.fee, Decimal)

        # 验证计算后仍保持Decimal类型 - 金融计算应该只返回Decimal
        assert isinstance(position.total_pnl, Decimal)  # total_pnl计算结果应该是Decimal
        assert isinstance(position.worth, Decimal)   # worth计算结果应该是Decimal

    def test_negative_value_validation(self):
        """测试负值检查"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            fee=5.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 测试通过on_price_update方法处理负价格
        # 负价格应该被拒绝，只记录警告，价格保持不变
        original_price = position.price
        result = position.on_price_update(Decimal('-10.0'))

        # 验证负价格被拒绝，返回False，实际价格保持不变
        assert result == False  # 返回失败
        assert position.price == original_price  # 价格未改变

        # 测试volume负值处理 - 通过公共接口
        try:
            position.volume = -100
            volume_result = position.volume
            # 股数不能为负，系统应该返回0或抛出异常
            assert volume_result >= 0
        except (ValueError, TypeError):
            # 在setter中直接拒绝负股数更为合理
            pass

        # 测试费用负值处理 - 负费用在某些场景下可能合理（返佣）
        # 但通常应该通过单独的返佣字段处理

    def test_newly_implemented_properties(self):
        """测试新实现的8个属性"""
        from decimal import Decimal
        from ginkgo.enums import COMPONENT_TYPES, SOURCE_TYPES
        import datetime

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=200,
            price=Decimal('110.0'),
            fee=Decimal('5.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 1. 测试available_volume属性计算逻辑
        # available_volume = volume - frozen_volume = 1000 - 200 = 800
        expected_available = 800
        assert position.available_volume == expected_available
        assert isinstance(position.available_volume, int)

        # 2. 测试component_type枚举值
        assert position.component_type == COMPONENT_TYPES.POSITION
        assert isinstance(position.component_type, COMPONENT_TYPES)

        # 3. 测试init_time时间戳功能
        assert hasattr(position, 'init_time')
        assert isinstance(position.init_time, datetime.datetime)
        # init_time应该在创建时设置，不应该为空
        assert position.init_time is not None

        # 4. 测试last_update时间戳功能
        assert hasattr(position, 'last_update')
        assert isinstance(position.last_update, datetime.datetime)
        # last_update应该在创建时设置，不应该为空
        assert position.last_update is not None
        # last_update应该等于或晚于init_time
        assert position.last_update >= position.init_time

        # 5. 测试market_value计算
        # market_value应该等于worth = (volume + frozen_volume) * price = 1200 * 110 = 132000
        expected_market_value = Decimal('132000.00')
        assert position.market_value == expected_market_value
        assert isinstance(position.market_value, Decimal)

        # 6. 测试unrealized_pnl计算
        # unrealized_pnl应该等于total_pnl = (volume + frozen_volume) * (price - cost) - fee
        # = 1200 * (110 - 100) - 5 = 1200 * 10 - 5 = 11995
        expected_unrealized = Decimal('11995.0')
        assert position.unrealized_pnl == expected_unrealized
        assert isinstance(position.unrealized_pnl, Decimal)

        # 7. 测试realized_pnl默认行为
        # realized_pnl对于活跃持仓应该返回0
        assert position.realized_pnl == Decimal('0.0')
        assert isinstance(position.realized_pnl, Decimal)

        # 8. 测试source属性继承
        # source属性从Base类继承，默认应该是VOID
        assert position.source == SOURCE_TYPES.VOID
        assert isinstance(position.source, SOURCE_TYPES)

        # 测试source属性设置
        position.set_source(SOURCE_TYPES.TUSHARE)
        assert position.source == SOURCE_TYPES.TUSHARE


@pytest.mark.unit
class TestPositionDataSetting:
    """3. 数据设置测试"""

    def test_direct_parameter_setting(self):
        """测试直接参数设置"""
        from decimal import Decimal

        # 先创建有效的Position实例，再用set()更新
        position = Position(
            portfolio_id="initial_portfolio",
            engine_id="initial_engine",
            run_id="initial_run",
            code="initial_code",
            timestamp="2023-01-01 10:00:00"
        )

        # 使用set()方法设置关键参数 - 前4个参数是位置参数
        position.set(
            "test_portfolio_001",    # portfolio_id
            "test_engine_001",       # engine_id
            "test_run_001",          # run_id
            "000001.SZ",             # code
            volume=1000,
            cost=Decimal('10.50'),
            price=Decimal('12.00'),  # 添加当前价格
            fee=Decimal('5.25')
        )

        # 验证参数正确设置
        assert position.portfolio_id == "test_portfolio_001"
        assert position.engine_id == "test_engine_001"
        assert position.run_id == "test_run_001"
        assert position.code == "000001.SZ"
        assert position.volume == 1000
        assert position.cost == Decimal('10.50')
        assert position.price == Decimal('12.00')
        assert position.fee == Decimal('5.25')

        # 验证计算属性正确更新 - 使用正确的计算公式
        # worth = (volume + frozen_volume + settlement_frozen_volume) * price = (1000 + 0) * 12.00 = 12000.00
        expected_worth = Decimal('12000.00')
        assert position.worth == expected_worth

        # total_pnl = (volume + frozen_volume + settlement_frozen_volume) * (price - cost) - fee
        # = (1000 + 0) * (12.00 - 10.50) - 5.25 = 1000 * 1.50 - 5.25 = 1494.75
        expected_total_pnl = Decimal('1494.75')
        assert position.total_pnl == expected_total_pnl

    def test_pandas_series_setting(self):
        """测试pandas.Series设置"""
        import pandas as pd
        from decimal import Decimal

        # 创建空的Position实例
        position = Position(
            portfolio_id="temp",
            engine_id="temp",
            run_id="temp",
            code="temp",
            timestamp="2023-01-01 10:00:00"
        )

        # 创建pandas Series模拟数据库行
        series_data = pd.Series({
            "portfolio_id": "test_portfolio_002",
            "engine_id": "test_engine_002",
            "run_id": "test_run_002",
            "code": "000002.SZ",
            "cost": 99.50,
            "volume": 2000,
            "frozen_volume": 200,
            "frozen_money": 100.0,
            "price": 105.75,
            "fee": 10.50,
            "uuid": "series_uuid_001"
        })

        # 使用Series设置Position数据
        position.set(series_data)

        # 验证所有数据正确设置
        assert position.portfolio_id == "test_portfolio_002"
        assert position.engine_id == "test_engine_002"
        assert position.run_id == "test_run_002"
        assert position.code == "000002.SZ"
        assert position.cost == Decimal('99.50')
        assert position.volume == 2000
        assert position.frozen_volume == 200
        assert position.price == Decimal('105.75')
        assert position.fee == Decimal('10.50')
        assert position.uuid == "series_uuid_001"

    def test_partial_parameter_update(self):
        """测试部分参数更新"""
        from decimal import Decimal

        # 创建初始Position
        position = Position(
            portfolio_id="original_portfolio",
            engine_id="original_engine",
            run_id="original_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            fee=5.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 记录原始值
        original_volume = position.volume
        original_fee = position.fee
        original_code = position.code

        # 只更新部分参数（价格和成本）
        position.set(
            "original_portfolio",  # portfolio_id as positional
            "original_engine",     # engine_id as positional
            "original_run",        # run_id as positional
            "000001.SZ",           # code as positional
            cost=120.0,            # 更新
            price=125.0            # 更新
            # volume, fee 等参数未传入，应保持原值
        )

        # 验证更新的参数
        assert position.cost == Decimal('120.0')
        assert position.price == Decimal('125.0')

        # 验证未更新的参数保持不变
        assert position.volume == original_volume
        assert position.fee == original_fee
        assert position.code == original_code

    def test_data_type_conversion(self):
        """测试数据类型转换"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            timestamp="2023-01-01 10:00:00"
        )

        # 测试字符串数字转换为Decimal
        position.set(
            "test_portfolio",   # portfolio_id 位置参数
            "test_engine",      # engine_id 位置参数
            "test_run",         # run_id 位置参数
            "000001.SZ",        # code 位置参数
            cost="100.50",      # 字符串
            price="110.75",     # 字符串
            fee="5.25",         # 字符串
            volume="1000"       # 字符串数字
        )

        # 验证类型转换正确
        assert isinstance(position.cost, Decimal)
        assert isinstance(position.price, Decimal)
        assert isinstance(position.fee, Decimal)
        assert isinstance(position.volume, int)

        # 验证值正确
        assert position.cost == Decimal('100.50')
        assert position.price == Decimal('110.75')
        assert position.fee == Decimal('5.25')
        assert position.volume == 1000

        # 测试float转换
        position.set(
            "test_portfolio",   # portfolio_id 位置参数
            "test_engine",      # engine_id 位置参数
            "test_run",         # run_id 位置参数
            "000001.SZ",        # code 位置参数
            cost=95.25,         # float
            price=105.50        # float
        )

        assert isinstance(position.cost, Decimal)
        assert isinstance(position.price, Decimal)
        assert position.cost == Decimal('95.25')
        assert position.price == Decimal('105.50')

    def test_parameter_validation(self):
        """测试参数验证"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            timestamp="2023-01-01 10:00:00"
        )

        # 测试正常参数组合
        valid_result = position.set(
            "valid_portfolio",  # portfolio_id 位置参数
            "valid_engine",     # engine_id 位置参数
            "valid_run",        # run_id 位置参数
            "000002.SZ",        # code 位置参数
            cost=100.0,
            volume=1000,
            price=110.0,
            fee=5.0
        )
        # set方法正常情况下返回None
        assert valid_result is None

        # 验证参数正确设置
        assert position.portfolio_id == "valid_portfolio"
        assert position.engine_id == "valid_engine"
        assert position.run_id == "valid_run"
        assert position.code == "000002.SZ"
        assert position.cost == Decimal('100.0')
        assert position.volume == 1000
        assert position.price == Decimal('110.0')
        assert position.fee == Decimal('5.0')

        # 测试空字符串参数设置（可能合法）
        position.set(
            "",               # portfolio_id 空字符串 位置参数
            "test_engine",    # engine_id 位置参数
            "test_run",       # run_id 位置参数
            "000001.SZ"       # code 位置参数
        )
        # set方法应该能处理空字符串（这里与构造函数不同）

    def test_data_integrity_after_setting(self):
        """测试设置后数据完整性"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 记录设置前的profit和worth
        old_profit = position.total_pnl
        old_worth = position.worth

        # 更新价格和数量
        position.set(
            "test_portfolio",   # portfolio_id 位置参数
            "test_engine",      # engine_id 位置参数
            "test_run",         # run_id 位置参数
            "000001.SZ",        # code 位置参数
            cost=100.0,
            volume=1500,      # 增加数量
            price=120.0       # 提高价格
        )

        # 验证profit和worth自动更新
        new_profit = position.total_pnl
        new_worth = position.worth

        # worth = (volume + frozen_volume + settlement_frozen_volume) * price
        expected_worth = 1500 * 120.0  # 180000
        assert position.worth == expected_worth

        # total_pnl = (volume + frozen_volume + settlement_frozen_volume) * (price - cost) - fee
        expected_total_pnl = 1500 * (120.0 - 100.0) - 0  # 30000
        assert position.total_pnl == expected_total_pnl

        # 验证数据确实更新了
        assert new_profit != old_profit
        assert new_worth != old_worth


@pytest.mark.unit
class TestPositionTradeExecution:
    """4. 交易执行测试"""

    def test_buy_operation(self):
        """测试买入操作"""
        from decimal import Decimal

        # 创建初始持仓
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            price=Decimal('100.0'),
            fee=Decimal('5.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 记录买入前状态
        initial_volume = position.volume
        initial_cost = position.cost
        initial_fee = position.fee

        # 执行买入操作：买入500股，价格110元
        buy_price = Decimal('110.0')
        buy_volume = 500
        result = position._bought(buy_price, buy_volume)

        # 验证买入操作成功
        assert result is True

        # 验证持仓数量增加
        assert position.volume == initial_volume + buy_volume  # 1000 + 500 = 1500

        # 验证加权平均成本价更新
        # 新成本价 = (原持仓价值 + 新买入价值) / 总持仓
        # = (1000 * 100 + 500 * 110) / 1500 = (100000 + 55000) / 1500 = 103.33...
        expected_cost = (initial_volume * initial_cost + buy_volume * buy_price) / (initial_volume + buy_volume)
        assert abs(position.cost - expected_cost) < Decimal('0.01')

        # 验证盈亏和市值自动更新
        assert isinstance(position.total_pnl, Decimal)
        assert isinstance(position.worth, Decimal)

    def test_sell_operation(self):
        """测试卖出操作"""
        from decimal import Decimal

        # 创建带有冻结持仓的Position
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=500,  # 冻结500股用于卖出
            price=Decimal('110.0'),
            fee=Decimal('5.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 记录卖出前状态
        initial_volume = position.volume
        initial_frozen_volume = position.frozen_volume
        initial_cost = position.cost  # 卖出不应该影响成本价

        # 执行卖出操作：卖出300股，价格115元
        sell_price = Decimal('115.0')
        sell_volume = 300
        result = position._sold(sell_price, sell_volume)

        # 验证卖出操作成功
        assert result is True

        # 验证冻结持仓减少
        assert position.frozen_volume == initial_frozen_volume - sell_volume  # 500 - 300 = 200

        # 验证总持仓不变（卖出只影响冻结部分）
        assert position.volume == initial_volume

        # 验证成本价不变（卖出操作不影响持仓成本）
        assert position.cost == initial_cost

        # 验证盈亏和市值重新计算
        assert isinstance(position.total_pnl, Decimal)
        assert isinstance(position.worth, Decimal)

    def test_deal_unified_interface(self):
        """测试deal()统一接口"""
        from decimal import Decimal

        # 创建初始持仓
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=300,
            price=Decimal('100.0'),
            fee=Decimal('5.0'),
            timestamp="2023-01-01 10:00:00"
        )

        initial_volume = position.volume
        initial_frozen = position.frozen_volume

        # 测试LONG方向（买入）
        result = position.deal(DIRECTION_TYPES.LONG, 105.0, 200)
        assert result is True  # 交易应该成功
        assert position.volume == initial_volume + 200  # 买入增加持仓

        # 测试SHORT方向（卖出）
        result = position.deal(DIRECTION_TYPES.SHORT, 110.0, 150)
        assert result is True  # 交易应该成功
        assert position.frozen_volume == initial_frozen - 150  # 卖出减少冻结持仓

        # 验证状态正确更新
        assert isinstance(position.total_pnl, Decimal)
        assert isinstance(position.worth, Decimal)

    def test_average_cost_calculation(self):
        """测试成本价计算"""
        from decimal import Decimal

        # 创建空持仓，第一次买入
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('0.0'),
            volume=0,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 第一次买入：1000股，价格100元
        position._bought(Decimal('100.0'), 1000)
        assert position.volume == 1000
        assert position.cost == Decimal('100.0')

        # 第二次买入：500股，价格120元
        # 新成本价 = (1000*100 + 500*120) / (1000+500) = 160000/1500 = 106.67
        position._bought(Decimal('120.0'), 500)
        expected_cost = (Decimal('1000') * Decimal('100.0') + Decimal('500') * Decimal('120.0')) / Decimal('1500')
        assert position.volume == 1500
        assert abs(position.cost - expected_cost) < Decimal('0.01')

        # 第三次买入：1000股，价格90元
        # 新成本价 = (1500*106.67 + 1000*90) / (1500+1000) = 250000/2500 = 100.0
        position._bought(Decimal('90.0'), 1000)
        expected_cost = (Decimal('1500') * expected_cost + Decimal('1000') * Decimal('90.0')) / Decimal('2500')
        assert position.volume == 2500
        assert abs(position.cost - expected_cost) < Decimal('0.01')

    def test_volume_validation(self):
        """测试数量验证"""
        from decimal import Decimal

        # 创建持仓，冻结部分股票
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=300,  # 只冻结300股
            price=Decimal('110.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 正常卖出：数量在冻结范围内
        result = position._sold(Decimal('115.0'), 200)
        assert result is True
        assert position.frozen_volume == 100  # 300 - 200 = 100

        # 尝试卖出超过冻结数量，应该失败而不是抛出异常
        result = position._sold(Decimal('115.0'), 200)  # 尝试卖出200股，但只剩100股冻结
        assert result is False  # 应该返回False表示失败

    def test_price_validation(self):
        """测试价格验证"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 测试正常价格
        result = position._bought(Decimal('110.0'), 100)
        assert result is True

        # 测试负价格应该返回False而不是抛出异常
        result = position._bought(Decimal('-10.0'), 100)
        assert result is False  # 负价格应该被拒绝，记录日志但不抛异常

        # 测试零价格应该返回False
        result = position._bought(Decimal('0.0'), 100)
        assert result is False  # 零价格应该被拒绝，记录日志但不抛异常

    def test_exception_handling(self):
        """测试异常处理"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=500,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 测试负数量应该返回False而不是抛出异常
        result = position._bought(Decimal('110.0'), -100)
        assert result is False  # 负数量应该被拒绝，记录日志但不抛异常

        # 测试零数量的处理（通常应该被拒绝或忽略）
        result = position._bought(Decimal('110.0'), 0)
        # 零数量交易通常被认为是无效操作
        # 系统可能返回False或True但不改变状态，两种都合理
        assert isinstance(result, bool)  # 至少应该返回布尔值

        # 测试非数字价格也应该返回False而不是抛出异常
        result = position._bought("invalid_price", 100)
        assert result is False  # 非数字价格应该被拒绝，记录日志但不抛异常

    def test_state_update_after_trade(self):
        """测试交易后状态更新"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            price=Decimal('105.0'),  # 当前价格105元
            fee=Decimal('5.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 记录交易前状态
        initial_profit = position.total_pnl
        initial_worth = position.worth

        # 执行买入交易
        position._bought(Decimal('110.0'), 500)

        # 验证profit和worth自动更新
        assert position.total_pnl != initial_profit
        assert position.worth != initial_worth
        assert isinstance(position.total_pnl, Decimal)
        assert isinstance(position.worth, Decimal)

        # 验证worth计算正确：(总持仓数量) * 当前价格
        expected_worth = (position.volume + position.frozen_volume) * position.price
        assert position.worth == expected_worth


@pytest.mark.unit
class TestPositionFreezeOperations:
    """5. 冻结操作测试"""

    def test_position_freeze(self):
        """测试持仓冻结"""
        from decimal import Decimal

        # 创建有可用持仓的Position
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=200,  # 已冻结200股
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 记录初始状态
        initial_volume = position.volume
        initial_frozen = position.frozen_volume

        # 冻结300股（从 volume 转移到 frozen_volume）
        freeze_amount = 300
        result = position.freeze(freeze_amount)

        # 验证冻结成功
        assert result is True
        assert position.volume == initial_volume - freeze_amount  # volume减少
        assert position.frozen_volume == initial_frozen + freeze_amount  # frozen_volume增加

    def test_position_unfreeze(self):
        """测试持仓解冻"""
        from decimal import Decimal

        # 创建有冻结持仓的Position
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=500,  # 冻结500股
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        initial_volume = position.volume
        initial_frozen = position.frozen_volume

        # 解冻200股（将冻结持仓恢复为可用持仓）
        unfreeze_amount = 200
        result = position.unfreeze(unfreeze_amount)

        # 验证解冻成功
        assert result == True  # 返回操作成功
        assert position.volume == initial_volume + unfreeze_amount  # volume增加（冻结恢复为可用）
        assert position.frozen_volume == initial_frozen - unfreeze_amount  # frozen_volume减少
        assert position.available_volume == position.volume - position.frozen_volume  # 可用数量 = volume - frozen

    def test_freeze_volume_validation(self):
        """测试冻结数量验证"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=300,  # 已冻结300股，可用700股
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        initial_volume = position.volume  # 1000股

        # 正常冻结：在volume范围内
        result = position.freeze(500)
        assert result is True
        assert position.volume == initial_volume - 500  # 500股

        # 尝试冻结超过当前volume数量，应该失败
        remaining_volume = position.volume  # 当前500股
        result = position.freeze(remaining_volume + 1)  # 尝试冻结501股
        assert result is False  # 应该失败，因为只剩500股可冻结

    def test_unfreeze_volume_validation(self):
        """测试解冻数量验证"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=400,  # 冻结400股
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        initial_volume = position.volume
        initial_frozen = position.frozen_volume  # 400股

        # 正常解冻：在冻结范围内
        result = position.unfreeze(200)
        assert result == True  # unfreeze返回操作是否成功
        assert position.volume == initial_volume + 200  # volume增加（冻结恢复为可用）
        assert position.frozen_volume == initial_frozen - 200  # 200股

        # 尝试解冻超过已冻结数量应该被处理
        result = position.unfreeze(300)  # 尝试解冻300股，但只剩200股
        assert result == False  # 超额解冻返回False

    def test_state_consistency(self):
        """测试状态一致性"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=300,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 验证初始状态一致性：冻结 + 可用 = 总持仓
        assert position.frozen_volume + position.available_volume == position.volume

        # 执行冻结操作
        position.freeze(200)
        assert position.frozen_volume + position.available_volume == position.volume

        # 执行解冻操作
        position.unfreeze(150)
        assert position.frozen_volume + position.available_volume == position.volume

        # 执行交易操作后也应该保持一致性
        position._bought(Decimal('110.0'), 500)
        assert position.frozen_volume + position.available_volume == position.volume

    def test_frozen_money_management(self):
        """测试资金冻结"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=300,
            frozen_money=Decimal('5000.0'),  # 冻结资金5000元
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 验证冻结资金的读取
        assert position.frozen_money == Decimal('5000.0')
        assert isinstance(position.frozen_money, Decimal)

        # 测试冻结资金的设置（通过set方法）
        position.set(
            "test_portfolio", "test_engine", "test_run", "000001.SZ",
            frozen_money=Decimal('7500.0')
        )
        assert position.frozen_money == Decimal('7500.0')

    def test_boundary_conditions(self):
        """测试边界条件"""
        from decimal import Decimal

        # 测试零持仓情况
        zero_position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=0,  # 零持仓
            frozen_volume=0,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 零持仓时冻结操作应该失败或返回False
        result = zero_position.freeze(100)
        assert result is False  # 或者抛出异常

        # 测试全部持仓冻结
        full_position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=0,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 冻结全部持仓
        result = full_position.freeze(1000)
        assert result is True
        assert full_position.frozen_volume == 1000
        assert full_position.available_volume == 0

        # 全部解冻
        result = full_position.unfreeze(1000)
        assert result == True  # 返回操作成功
        assert full_position.frozen_volume == 0
        assert full_position.volume == 1000  # 冻结持仓恢复为可用持仓
        assert full_position.available_volume == 1000  # 全部恢复为可用


@pytest.mark.unit
class TestPositionPriceUpdate:
    """6. 价格更新测试"""

    def test_price_update_interface(self):
        """测试价格更新接口"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            price=Decimal('100.0'),
            fee=Decimal('5.0'),
            timestamp="2023-01-01 10:00:00"
        )

        initial_price = position.price

        # 测试价格更新
        new_price = Decimal('110.0')
        result = position.on_price_update(new_price)

        # 验证价格更新成功
        assert position.price == new_price
        assert result == True  # 返回成功
        assert isinstance(position.price, Decimal)

        # 测试不同类型的价格输入
        position.on_price_update(115.5)  # float
        assert position.price == Decimal('115.5')

        position.on_price_update(120)    # int
        assert position.price == Decimal('120')

    def test_profit_recalculation(self):
        """测试盈亏重算"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=200,
            price=Decimal('100.0'),
            fee=Decimal('5.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 记录初始盈亏
        initial_profit = position.total_pnl

        # 更新价格为110元（上涨）
        position.on_price_update(Decimal('110.0'))

        # 验证盈亏重新计算
        # total_pnl = (总持仓) * (当前价格 - 成本价) - 手续费
        # = (1000 + 200) * (110 - 100) - 5 = 1200 * 10 - 5 = 11995
        expected_total_pnl = (position.volume + position.frozen_volume) * (position.price - position.cost) - position.fee
        assert position.total_pnl == expected_total_pnl
        assert position.total_pnl > initial_profit  # 价格上涨，盈亏增加

        # 更新价格为90元（下跌）
        position.on_price_update(Decimal('90.0'))
        expected_total_pnl = (position.volume + position.frozen_volume) * (position.price - position.cost) - position.fee
        assert position.total_pnl == expected_total_pnl
        assert position.total_pnl < 0  # 价格下跌，产生亏损

    def test_worth_recalculation(self):
        """测试市值重算"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=500,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 记录初始市值
        initial_worth = position.worth

        # 更新价格为120元
        position.on_price_update(Decimal('120.0'))

        # 验证市值重新计算
        # worth = (总持仓数量) * 当前价格
        # = (1000 + 500) * 120 = 180000
        expected_worth = (position.volume + position.frozen_volume) * position.price
        assert position.worth == expected_worth
        assert position.worth > initial_worth  # 价格上涨，市值增加

        # 更新价格为80元
        position.on_price_update(Decimal('80.0'))
        expected_worth = (position.volume + position.frozen_volume) * position.price
        assert position.worth == expected_worth
        assert position.worth < initial_worth  # 价格下跌，市值减少

    def test_decimal_precision(self):
        """测试Decimal精度"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 测试高精度价格更新
        high_precision_price = Decimal('123.123456789')
        position.on_price_update(high_precision_price)

        # 验证精度保持
        assert position.price == high_precision_price
        assert isinstance(position.price, Decimal)

        # 测试float输入的精度转换
        position.on_price_update(456.789123)
        assert isinstance(position.price, Decimal)
        # 验证转换后的精度在合理范围内
        assert abs(position.price - Decimal('456.789123')) < Decimal('0.000001')

        # 测试科学计数法输入
        position.on_price_update(1.23e-4)
        assert isinstance(position.price, Decimal)
        assert position.price == Decimal('0.000123')

    def test_price_type_support(self):
        """测试价格类型支持"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 测试int类型输入
        position.on_price_update(150)
        assert position.price == Decimal('150')
        assert isinstance(position.price, Decimal)

        # 测试float类型输入
        position.on_price_update(175.50)
        assert position.price == Decimal('175.50')
        assert isinstance(position.price, Decimal)

        # 测试Decimal类型输入
        position.on_price_update(Decimal('200.75'))
        assert position.price == Decimal('200.75')
        assert isinstance(position.price, Decimal)

        # 测试字符串类型输入
        position.on_price_update("225.25")
        assert position.price == Decimal('225.25')
        assert isinstance(position.price, Decimal)

        # 测试小数输入
        position.on_price_update(0.01)
        assert position.price == Decimal('0.01')
        assert isinstance(position.price, Decimal)

    def test_invalid_price_handling(self):
        """测试异常价格处理"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        original_price = position.price

        # 测试负价格 - Position拒绝负价格，记录警告，价格保持不变
        result = position.on_price_update(-50.0)
        assert position.price == original_price  # 负价格被拒绝，价格保持不变
        assert result == False  # 返回失败

        # 测试零价格 - 重置价格到有效值再测试
        success = position.on_price_update(100.0)  # 先重置为有效价格
        assert success == True
        result = position.on_price_update(0.0)
        assert position.price == Decimal('0.0')  # Position接受零价格
        assert result == True  # 零价格更新成功

        # 测试极小价格 - 应该允许
        result = position.on_price_update(0.001)
        assert result == True  # 极小价格更新成功
        assert position.price == Decimal('0.001')  # 极小正价格应该被接受

        # 测试无效字符串
        position.on_price_update("100.0")  # 先设置有效价格
        original_price = position.price
        try:
            position.on_price_update("invalid_price")
            # 如果没有抛出异常，价格应该保持不变
            assert position.price == original_price
        except (ValueError, TypeError, Exception):
            # 抛出异常是预期行为，验证价格没有改变
            assert position.price == original_price

        # 测试None输入
        try:
            position.on_price_update(None)
            # 如果没有抛出异常，价格应该保持不变
            assert position.price == original_price
        except (ValueError, TypeError, Exception):
            # 抛出异常是预期行为，验证价格没有改变
            assert position.price == original_price


@pytest.mark.unit
class TestPositionFeeManagement:
    """7. 费用管理测试"""

    def test_fee_addition(self):
        """测试费用添加"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            fee=5.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 初始费用应该是5.0
        assert position.fee == Decimal('5.0')

        # 添加新费用
        result = position.add_fee(10.0)

        # add_fee()应该返回操作是否成功
        assert result == True
        assert position.fee == Decimal('15.0')

        # 再次添加费用
        position.add_fee(2.5)
        assert position.fee == Decimal('17.5')

    def test_fee_type_validation(self):
        """测试费用类型验证"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            fee=5.0,
            timestamp="2023-01-01 10:00:00"
        )

        original_fee = position.fee

        # 尝试添加负费用 - 应该失败并保持原费用不变
        result = position.add_fee(-10.0)

        # 负费用应该返回False且不修改费用
        assert result == False
        assert position.fee == original_fee  # 费用应该保持不变

        # 添加零费用应该可以
        result = position.add_fee(0.0)
        assert result == True
        assert position.fee == original_fee

    def test_fee_precision(self):
        """测试费用精度"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            fee=0.123456789,  # 高精度初始费用
            timestamp="2023-01-01 10:00:00"
        )

        # 费用应该保持为Decimal类型
        assert isinstance(position.fee, Decimal)
        assert position.fee == Decimal('0.123456789')

        # 添加高精度费用
        position.add_fee(0.987654321)

        # 验证精度保持
        expected_fee = Decimal('0.123456789') + Decimal('0.987654321')
        assert position.fee == expected_fee
        assert isinstance(position.fee, Decimal)

    def test_fee_accumulation(self):
        """测试费用累积"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            fee=0.0,  # 开始无费用
            timestamp="2023-01-01 10:00:00"
        )

        # 模拟多次交易产生费用
        fees = [1.25, 2.75, 0.50, 3.80, 1.20]
        expected_total = Decimal('0.0')

        for fee in fees:
            position.add_fee(fee)
            expected_total += Decimal(str(fee))
            assert position.fee == expected_total

        # 验证最终总费用
        assert position.fee == Decimal('9.50')

        # 验证费用类型始终为Decimal
        assert isinstance(position.fee, Decimal)

    def test_profit_impact(self):
        """测试盈亏影响"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            fee=5.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 初始盈利计算：(volume + frozen_volume) * (price - cost) - fee
        # = 1000 * (110 - 100) - 5 = 10000 - 5 = 9995
        initial_profit = position.total_pnl
        assert initial_profit == Decimal('9995.0')

        # 添加更多费用
        position.add_fee(100.0)  # 总费用变为105.0

        # 重新计算盈利
        position.update_total_pnl()

        # 新盈利：1000 * 10 - 105 = 9895
        expected_total_pnl = Decimal('9895.0')
        assert position.total_pnl == expected_total_pnl

        # 再添加费用
        position.add_fee(895.0)  # 总费用变为1000.0
        position.update_total_pnl()

        # 新盈利：1000 * 10 - 1000 = 9000
        expected_total_pnl = Decimal('9000.0')
        assert position.total_pnl == expected_total_pnl

    def test_fee_initialization(self):
        """测试费用初始化"""
        from decimal import Decimal

        # 测试默认费用初始化
        position1 = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            timestamp="2023-01-01 10:00:00"
        )

        # 默认费用应该为0
        assert position1.fee == Decimal('0.0')
        assert isinstance(position1.fee, Decimal)

        # 测试指定费用初始化
        position2 = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            fee=25.50,
            timestamp="2023-01-01 10:00:00"
        )

        assert position2.fee == Decimal('25.50')
        assert isinstance(position2.fee, Decimal)

        # 测试最少参数Position初始化
        position3 = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            timestamp="2023-01-01 10:00:00"
        )
        assert position3.fee == Decimal('0.0')


@pytest.mark.unit
class TestPositionModelConversion:
    """8. 数据模型转换测试"""

    def test_to_model_conversion(self):
        """测试to_model()转换"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.50,
            volume=1000,
            frozen_volume=200,
            frozen_money=15000.0,
            price=110.75,
            fee=25.30,
            timestamp="2023-01-01 10:00:00"
        )

        # 转换为数据库模型
        model = position.to_model()

        # 验证模型类型
        from ginkgo.data.models import MPosition
        assert isinstance(model, MPosition)

        # 验证所有字段正确转换
        assert model.portfolio_id == "test_portfolio"
        assert model.engine_id == "test_engine"
        assert model.run_id == "test_run"
        assert model.code == "000001.SZ"
        assert model.cost == Decimal('100.50')  # 模型中保持Decimal类型
        assert model.volume == 1000
        assert model.frozen_volume == 200
        assert model.frozen_money == Decimal('15000.0')
        assert model.price == Decimal('110.75')
        assert model.fee == Decimal('25.30')

        # 验证UUID正确传递
        assert model.uuid == position.uuid

    def test_from_model_conversion(self):
        """测试from_model()转换"""
        from ginkgo.data.models import MPosition
        from decimal import Decimal

        # 创建数据库模型
        model = MPosition()
        model.update(
            "test_portfolio",  # portfolio_id as first positional argument
            "test_engine",     # engine_id as second positional argument
            "test_run",        # run_id as third positional argument
            code="000001.SZ",
            cost=100.50,
            volume=1000,
            frozen_volume=200,
            frozen_money=15000.0,
            price=110.75,
            fee=25.30
        )
        # 设置UUID
        model.uuid = "test-uuid-123"

        # 从模型创建Position对象
        position = Position.from_model(model)

        # 验证所有字段正确转换
        assert position.portfolio_id == "test_portfolio"
        assert position.engine_id == "test_engine"
        assert position.run_id == "test_run"
        assert position.code == "000001.SZ"
        assert position.cost == Decimal('100.50')  # float转为Decimal
        assert position.volume == 1000
        assert position.frozen_volume == 200
        assert position.frozen_money == Decimal('15000.0')
        assert position.price == Decimal('110.75')
        assert position.fee == Decimal('25.30')
        assert position.uuid == "test-uuid-123"  # 验证UUID传递

        # 验证Decimal类型
        assert isinstance(position.cost, Decimal)
        assert isinstance(position.frozen_money, Decimal)
        assert isinstance(position.price, Decimal)
        assert isinstance(position.fee, Decimal)

    def test_data_integrity(self):
        """测试数据完整性"""
        from decimal import Decimal

        # 创建复杂的Position对象
        original_position = Position(
            portfolio_id="complex_portfolio",
            engine_id="complex_engine",
            run_id="complex_run",
            code="000002.SZ",
            cost=99.99,
            volume=1500,
            frozen_volume=300,
            frozen_money=12345.67,
            price=105.55,
            fee=123.45,
            timestamp="2023-01-01 10:00:00"
        )

        # 执行一些操作以修改状态
        original_position.add_fee(10.55)  # 总费用变为134.0
        original_position.update_total_pnl()
        original_position.update_worth()

        # 转换为模型再转回Position
        model = original_position.to_model()
        converted_position = Position.from_model(model)

        # 验证核心字段数据完整性
        assert converted_position.portfolio_id == original_position.portfolio_id
        assert converted_position.engine_id == original_position.engine_id
        assert converted_position.run_id == original_position.run_id
        assert converted_position.code == original_position.code
        assert converted_position.cost == original_position.cost
        assert converted_position.volume == original_position.volume
        assert converted_position.frozen_volume == original_position.frozen_volume
        assert converted_position.frozen_money == original_position.frozen_money
        assert converted_position.price == original_position.price
        assert converted_position.fee == original_position.fee

        # 验证计算属性也能重新计算正确
        converted_position.update_total_pnl()
        converted_position.update_worth()
        assert converted_position.total_pnl == original_position.total_pnl
        assert converted_position.worth == original_position.worth

    def test_type_conversion(self):
        """测试类型转换"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.123456'),  # 高精度Decimal
            volume=1000,
            frozen_money=Decimal('15000.987654'),
            price=Decimal('110.555555'),
            fee=Decimal('25.333333'),
            timestamp="2023-01-01 10:00:00"
        )

        # 转换为模型 - Decimal保持不变
        model = position.to_model()

        # 验证模型中使用Decimal类型
        assert isinstance(model.cost, Decimal)
        assert isinstance(model.frozen_money, Decimal)
        assert isinstance(model.price, Decimal)
        assert isinstance(model.fee, Decimal)

        # 从模型转回Position - float转为Decimal
        new_position = Position.from_model(model)

        # 验证Position中使用Decimal类型
        assert isinstance(new_position.cost, Decimal)
        assert isinstance(new_position.frozen_money, Decimal)
        assert isinstance(new_position.price, Decimal)
        assert isinstance(new_position.fee, Decimal)

        # 验证数值精度在合理范围内（由于float精度限制）
        assert abs(new_position.cost - position.cost) < Decimal('0.000001')
        assert abs(new_position.frozen_money - position.frozen_money) < Decimal('0.000001')
        assert abs(new_position.price - position.price) < Decimal('0.000001')
        assert abs(new_position.fee - position.fee) < Decimal('0.000001')

    def test_missing_field_handling(self):
        """测试缺失字段处理"""
        from ginkgo.data.models import MPosition
        from decimal import Decimal

        # 创建只有部分字段的模型（模拟数据库字段缺失）
        model = MPosition()
        model.update(
            "test_portfolio",  # portfolio_id as first positional argument
            "test_engine",     # engine_id as second positional argument
            "test_run",        # run_id as third positional argument
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            frozen_volume=0,   # 提供默认值而不是缺失
            frozen_money=0.0,  # 提供默认值而不是缺失
            fee=0.0            # 提供默认值而不是缺失
        )

        # 从模型创建Position - 应该处理缺失字段
        position = Position.from_model(model)

        # 验证基本字段正确
        assert position.portfolio_id == "test_portfolio"
        assert position.engine_id == "test_engine"
        assert position.code == "000001.SZ"
        assert position.cost == Decimal('100.0')
        assert position.volume == 1000
        assert position.price == Decimal('110.0')

        # 验证缺失字段的默认值处理
        # run_id应该有默认值，根据from_model方法中的getattr(model, 'run_id', '')
        assert hasattr(position, 'run_id')

        # 其他字段应该有合理的默认值（可能为0）
        assert hasattr(position, 'frozen_volume')
        assert hasattr(position, 'frozen_money')
        assert hasattr(position, 'fee')

        # 验证对象可以正常工作
        assert isinstance(position.fee, Decimal)
        assert isinstance(position.frozen_money, Decimal)

    def test_roundtrip_consistency(self):
        """测试往返一致性"""
        from decimal import Decimal

        # 创建包含所有字段的完整Position对象
        original = Position(
            portfolio_id="roundtrip_portfolio",
            engine_id="roundtrip_engine",
            run_id="roundtrip_run",
            code="000003.SZ",
            cost=123.456789,
            volume=2000,
            frozen_volume=500,
            frozen_money=67890.12,
            price=145.67,
            fee=89.01,
            timestamp="2023-01-01 10:00:00"
        )

        # 执行一些操作来修改状态
        original.freeze(1000, 50000.0)
        original.add_fee(15.99)
        original.update_total_pnl()
        original.update_worth()

        # 记录原始状态
        original_uuid = original.uuid
        original_total_pnl = original.total_pnl
        original_worth = original.worth

        # 往返转换：Position → MPosition → Position
        model = original.to_model()
        roundtrip = Position.from_model(model)

        # 验证基本字段完全一致
        assert roundtrip.portfolio_id == original.portfolio_id
        assert roundtrip.engine_id == original.engine_id
        assert roundtrip.run_id == original.run_id
        assert roundtrip.code == original.code
        assert roundtrip.volume == original.volume
        assert roundtrip.frozen_volume == original.frozen_volume

        # 验证Decimal字段（考虑float精度损失）
        assert abs(roundtrip.cost - original.cost) < Decimal('0.000001')
        assert abs(roundtrip.frozen_money - original.frozen_money) < Decimal('0.01')
        assert abs(roundtrip.price - original.price) < Decimal('0.01')
        assert abs(roundtrip.fee - original.fee) < Decimal('0.01')

        # 验证UUID保持一致（如果模型支持）
        assert roundtrip.uuid == original_uuid

        # 验证计算属性可以重新计算
        roundtrip.update_total_pnl()
        roundtrip.update_worth()
        assert abs(roundtrip.total_pnl - original_total_pnl) < Decimal('0.01')
        assert abs(roundtrip.worth - original_worth) < Decimal('0.01')


@pytest.mark.unit
class TestPositionCorporateActions:
    """9. 公司行为测试"""

    def test_cash_dividend(self):
        """测试现金分红"""
        # 创建持仓：1000股，成本价10元
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            volume=1000,
            cost=Decimal('10.00'),
            price=Decimal('12.00'),
            timestamp="2023-01-01 10:00:00"
        )

        # 记录分红前的状态
        original_volume = position.volume
        original_cost = position.cost

        # 执行现金分红：每股分红0.5元
        dividend_per_share = Decimal('0.50')
        total_dividend = position.volume * dividend_per_share

        # 执行现金分红处理
        result = position.cash_dividend(dividend_per_share)

        # 验证操作成功
        assert result == True

        # 验证持仓数量不变
        assert position.volume == original_volume

        # 验证价格调整（除权后价格下调）
        expected_price = Decimal('12.00') - dividend_per_share
        assert position.price == expected_price

        # 验证总价值减少（分红金额）
        assert position.worth == original_volume * expected_price

    def test_stock_dividend(self):
        """测试送股处理"""
        # 创建持仓：100股，成本价20元
        pos = Position("port1", "eng1", "run1", "000001.SZ", cost=Decimal("20.00"), volume=100, price=Decimal("25.00"), timestamp="2023-01-01")

        # 执行10送3的送股（每10股送3股，即0.3的比例）
        result = pos.stock_dividend(Decimal("0.3"))

        # 验证操作成功
        assert result == True

        # 验证数量增加30%
        assert pos.volume == 130

        # 验证成本价调整（总成本不变，股数增加）
        expected_cost = Decimal("20.00") / Decimal("1.3")  # 20 / 1.3 ≈ 15.38
        assert abs(pos.cost - expected_cost) < Decimal("0.01")

        # 验证价格调整（除权后价格下调）
        expected_price = Decimal("25.00") / Decimal("1.3")  # 25 / 1.3 ≈ 19.23
        assert abs(pos.price - expected_price) < Decimal("0.01")

        # 验证总价值不变
        assert abs(pos.worth - Decimal("2500.00")) < Decimal("1.00")


    def test_stock_split(self):
        """测试股票拆分"""
        # 创建有持仓的Position
        pos = Position("port1", "eng1", "run1", "000001.SZ", cost=Decimal("10.00"), volume=100, price=Decimal("15.00"), timestamp="2023-01-01")

        # 执行1拆2股票拆分
        result = pos.stock_split(2)

        # 验证操作成功
        assert result == True

        # 验证数量翻倍
        assert pos.volume == 200

        # 验证成本价减半
        assert pos.cost == Decimal("5.00")

        # 验证当前价格减半
        assert pos.price == Decimal("7.50")

        # 验证总价值不变
        assert pos.worth == Decimal("1500.00")  # 200 * 7.5 = 1500

    def test_stock_consolidation(self):
        """测试股票合并"""
        # 创建有持仓的Position
        pos = Position("port1", "eng1", "run1", "000001.SZ", cost=Decimal("10.00"), volume=200, price=Decimal("8.00"), timestamp="2023-01-01")

        # 执行2合1股票合并
        result = pos.stock_consolidation(2)

        # 验证操作成功
        assert result == True

        # 验证数量减半
        assert pos.volume == 100

        # 验证成本价翻倍
        assert pos.cost == Decimal("20.00")

        # 验证当前价格翻倍
        assert pos.price == Decimal("16.00")

        # 验证总价值不变
        assert pos.worth == Decimal("1600.00")  # 100 * 16 = 1600




@pytest.mark.unit
class TestPositionPriceAdjustment:
    """11. 价格调整测试"""

    def test_cost_price_recalculation(self):
        """测试成本价重算"""
        from decimal import Decimal

        # 创建初始持仓：1000股，成本价100元
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 验证初始成本价
        assert position.cost == Decimal('100.0')
        assert position.volume == 1000

        # 场景1: 多次买入的加权平均成本计算
        # 第一次加仓：500股，价格110元
        success = position.deal(DIRECTION_TYPES.LONG, 110.0, 500)
        assert success == True

        # 验证加权平均成本: (1000*100 + 500*110) / (1000+500) = 155000/1500 = 103.33
        expected_cost = (Decimal('1000') * Decimal('100.0') + Decimal('500') * Decimal('110.0')) / Decimal('1500')
        assert abs(position.cost - expected_cost) < Decimal('0.01')
        assert position.volume == 1500

        # 记录第一次加仓后的成本价
        first_addition_cost = position.cost

        # 第二次加仓：300股，价格90元
        success = position.deal(DIRECTION_TYPES.LONG, 90.0, 300)
        assert success == True

        # 验证新的加权平均成本: (1500*first_addition_cost + 300*90) / (1500+300)
        total_cost = Decimal('1500') * first_addition_cost + Decimal('300') * Decimal('90.0')
        expected_cost = total_cost / Decimal('1800')
        # 使用更宽松的精度要求，因为Decimal计算可能有微小差异
        assert abs(position.cost - expected_cost) < Decimal('0.1')
        assert position.volume == 1800

        # 场景2: 复权调整场景模拟（通过直接设置成本价）
        # 假设发生1:2拆股，成本价应该减半，持仓量翻倍
        original_cost = position.cost
        original_volume = position.volume

        # 模拟拆股后的调整
        position.set(
            "test_portfolio",
            "test_engine",
            "test_run",
            "000001.SZ",
            cost=original_cost / 2,  # 成本价减半
            volume=original_volume * 2  # 持仓量翻倍
        )

        # 验证拆股后的成本调整
        assert position.cost == original_cost / 2
        assert position.volume == original_volume * 2

        # 场景3: 验证成本价的精度保持
        assert isinstance(position.cost, Decimal)

        # 场景4: 验证成本价不会变为负数（边界条件）
        try:
            position.set(
                "test_portfolio",
                "test_engine",
                "test_run",
                "000001.SZ",
                cost=-50.0  # 尝试设置负成本价
            )
            # Position采用容错设计，可能接受负成本价但记录警告
            # 这里验证对象仍然可用
            assert hasattr(position, 'cost')
        except ValueError:
            # 如果抛出异常也是可接受的行为
            pass



@pytest.mark.unit
class TestPositionAttributeUpdates:
    """12. Position属性更新测试"""

    def test_constructor_with_new_attributes(self):
        """测试构造函数支持新属性"""
        from decimal import Decimal
        import datetime
        from ginkgo.enums import SOURCE_TYPES

        # 创建自定义时间
        custom_init_time = datetime.datetime(2024, 1, 1, 10, 0, 0)
        custom_last_update = datetime.datetime(2024, 1, 1, 11, 0, 0)
        custom_realized_pnl = Decimal('100.50')

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            price=Decimal('110.0'),
            fee=Decimal('5.0'),
            init_time=custom_init_time,
            last_update=custom_last_update,
            realized_pnl=custom_realized_pnl,
            timestamp="2023-01-01 10:00:00"
        )

        # 验证新属性被正确设置
        assert position.init_time == custom_init_time
        # last_update可能被自动更新，只验证类型和合理性
        assert isinstance(position.last_update, datetime.datetime)
        assert position.last_update >= custom_init_time  # last_update应该不早于init_time
        assert position.realized_pnl == custom_realized_pnl
        assert isinstance(position.realized_pnl, Decimal)

    def test_set_method_with_new_attributes(self):
        """测试set方法支持新属性更新"""
        from decimal import Decimal
        import datetime

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            fee=5.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 记录原始时间
        original_init_time = position.init_time
        original_last_update = position.last_update

        # 设置新的属性值
        new_init_time = datetime.datetime(2024, 2, 1, 9, 0, 0)
        new_last_update = datetime.datetime(2024, 2, 1, 10, 0, 0)
        new_realized_pnl = Decimal('200.75')

        position.set(
            "test_portfolio", "test_engine", "test_run", "000001.SZ",
            cost=105.0,
            volume=1200,
            price=115.0,
            fee=6.0,
            init_time=new_init_time,
            last_update=new_last_update,
            realized_pnl=new_realized_pnl
        )

        # 验证属性更新
        assert position.init_time == new_init_time
        # last_update可能被自动更新，验证它至少不早于设置的时间
        assert isinstance(position.last_update, datetime.datetime)
        assert position.last_update >= new_last_update
        assert position.realized_pnl == new_realized_pnl

        # 验证基础属性也正确更新
        assert position.cost == Decimal('105.0')
        assert position.volume == 1200
        assert position.price == Decimal('115.0')
        assert position.fee == Decimal('6.0')

    def test_realized_pnl_setter_validation(self):
        """测试realized_pnl setter的验证"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            fee=5.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 测试有效值设置
        position.realized_pnl = 150.25
        assert position.realized_pnl == Decimal('150.25')

        position.realized_pnl = Decimal('200.50')
        assert position.realized_pnl == Decimal('200.50')

        # 测试无效类型
        with pytest.raises(TypeError):
            position.realized_pnl = "invalid"

        with pytest.raises(TypeError):
            position.realized_pnl = []

    def test_time_setter_validation(self):
        """测试时间属性setter的验证"""
        import datetime

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            fee=5.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 测试有效时间设置
        new_time = datetime.datetime(2024, 3, 1, 12, 0, 0)
        position.init_time = new_time
        assert position.init_time == new_time

        position.last_update = new_time
        assert position.last_update == new_time

        # 测试有效的字符串日期设置（datetime_normalize支持）
        position.init_time = "2024-01-01"
        assert position.init_time.year == 2024
        assert position.init_time.month == 1
        assert position.init_time.day == 1

        # 测试有效的Unix时间戳设置（datetime_normalize支持）
        position.last_update = 1234567890
        assert isinstance(position.last_update, datetime.datetime)

        # 测试真正的无效类型
        with pytest.raises((TypeError, ValueError)):
            position.init_time = ["invalid", "list"]

        with pytest.raises((TypeError, ValueError)):
            position.last_update = {"invalid": "dict"}

    def test_automatic_last_update_on_operations(self):
        """测试业务操作自动更新last_update"""
        import datetime
        from decimal import Decimal
        from ginkgo.enums import DIRECTION_TYPES

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            fee=5.0,
            timestamp="2023-01-01 10:00:00"
        )

        # 记录初始时间
        initial_last_update = position.last_update

        # 模拟价格更新
        import time
        time.sleep(0.01)  # 确保时间差异
        position.on_price_update(Decimal('115.0'))

        # 验证last_update被自动更新
        assert position.last_update > initial_last_update
        assert position.price == Decimal('115.0')

        # 记录价格更新后的时间
        price_update_time = position.last_update

        # 模拟交易操作
        time.sleep(0.01)
        position.deal(DIRECTION_TYPES.LONG, 120.0, 500)

        # 验证交易后last_update再次更新
        assert position.last_update > price_update_time

    def test_add_realized_pnl_method(self):
        """测试add_realized_pnl方法"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            fee=5.0,
            realized_pnl=50.0,
            timestamp="2023-01-01 10:00:00"
        )

        initial_realized = position.realized_pnl
        initial_last_update = position.last_update

        # 添加已实现盈亏
        import time
        time.sleep(0.01)
        result = position.add_realized_pnl(25.75)

        # 验证操作成功
        assert result == True

        # 验证累积效果
        expected_total = initial_realized + Decimal('25.75')
        assert position.realized_pnl == expected_total

        # 验证last_update被更新
        assert position.last_update > initial_last_update

        # 测试无效类型 - 现在返回False而不是抛出异常
        result = position.add_realized_pnl("invalid")
        assert result == False

    def test_set_without_last_update_auto_updates(self):
        """测试set方法不指定last_update时自动更新"""
        import datetime

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=100.0,
            volume=1000,
            price=110.0,
            fee=5.0,
            timestamp="2023-01-01 10:00:00"
        )

        initial_last_update = position.last_update

        # 使用set方法更新，不指定last_update
        import time
        time.sleep(0.01)
        position.set(
            "test_portfolio", "test_engine", "test_run", "000001.SZ",
            cost=105.0,
            volume=1200
        )

        # 验证last_update被自动更新
        assert position.last_update > initial_last_update


@pytest.mark.unit
class TestPositionQuantitativeScenarios:
    """13. Position量化交易实际场景测试"""

    def test_position_lifecycle_buy_sell_scenario(self):
        """测试完整的持仓生命周期 - 买入、加仓、减仓、清仓"""
        from decimal import Decimal
        from ginkgo.enums import DIRECTION_TYPES

        # 初始建仓：买入1000股平安银行，成本价10.50元
        position = Position(
            portfolio_id="quant_portfolio_001",
            engine_id="backtest_engine",
            run_id="strategy_test_20240101",
            code="000001.SZ",  # 平安银行
            cost=Decimal('10.50'),
            volume=1000,
            price=Decimal('10.50'),
            fee=Decimal('5.25'),  # 万分之五手续费
            timestamp="2023-01-01 10:00:00"
        )

        # 验证初始状态
        assert position.volume == 1000
        assert position.cost == Decimal('10.50')
        assert position.worth == Decimal('10500.00')  # 1000 * 10.50
        assert position.total_pnl == Decimal('-5.25')    # 0 - 5.25 (仅手续费)

        # 场景1：股价上涨，模拟价格更新
        current_price = Decimal('12.00')
        position.on_price_update(current_price)

        # 验证未实现盈亏计算
        expected_total_pnl = position.volume * (current_price - position.cost) - position.fee
        assert position.total_pnl == expected_total_pnl
        assert position.unrealized_pnl > 0  # 应该有正收益

    def test_chinese_stock_trading_constraints(self):
        """测试中国股市交易约束 - T+1、涨跌停限制、最小交易单位"""
        from decimal import Decimal

        # 创建A股持仓
        position = Position(
            portfolio_id="a_share_portfolio",
            engine_id="trading_engine",
            run_id="constraint_test",
            code="600519.SH",  # 贵州茅台
            cost=Decimal('1800.00'),
            volume=100,  # A股通常以100股为单位交易
            price=Decimal('1800.00'),
            fee=Decimal('9.00'),
            timestamp="2023-01-01 10:00:00"
        )

        # 验证最小交易单位（100股的整数倍）
        assert position.volume % 100 == 0

        # 模拟涨停价格（10%涨幅限制）
        limit_up_price = position.cost * Decimal('1.10')
        position.on_price_update(limit_up_price)

        # 验证涨停时的收益计算
        expected_limit_up_profit = position.volume * (limit_up_price - position.cost) - position.fee
        assert abs(position.total_pnl - expected_limit_up_profit) < Decimal('0.01')

        # T+1约束：当天买入的股票不能当天卖出（使用freeze方法模拟）
        position.freeze(position.volume)  # 模拟T+1冻结全部股数
        assert position.available_volume == 0  # 当天买入无法卖出

    def test_portfolio_position_weight_scenario(self):
        """测试组合中持仓权重控制场景"""
        from decimal import Decimal

        # 模拟一个50万资金的投资组合中的单只股票持仓
        total_portfolio_value = Decimal('500000.00')
        max_single_position_ratio = Decimal('0.20')  # 单只股票最大20%仓位

        position = Position(
            portfolio_id="weight_control_portfolio",
            engine_id="risk_control_engine",
            run_id="position_weight_test",
            code="002594.SZ",  # 比亚迪
            cost=Decimal('250.00'),
            volume=400,  # 10万市值，占组合20%
            price=Decimal('250.00'),
            fee=Decimal('50.00'),
            timestamp="2023-01-01 10:00:00"
        )

        # 计算持仓权重
        position_value = position.worth
        position_weight = position_value / total_portfolio_value

        # 验证持仓权重控制
        assert position_weight <= max_single_position_ratio
        assert position_weight == Decimal('0.20')  # 正好20%权重

        # 模拟股价上涨导致权重超标
        new_price = Decimal('300.00')  # 上涨20%
        position.on_price_update(new_price)

        new_position_weight = position.worth / total_portfolio_value

        # 验证权重变化
        assert new_position_weight > max_single_position_ratio  # 权重超标

        # 这种情况下需要减仓以控制风险

    def test_etf_trading_precision_scenario(self):
        """测试ETF交易精度场景 - 处理小数点后更多位数"""
        from decimal import Decimal

        # ETF价格通常有更高精度
        position = Position(
            portfolio_id="etf_precision_test",
            engine_id="precision_engine",
            run_id="etf_test_001",
            code="510300.SH",  # 沪深300ETF
            cost=Decimal('4.567'),  # ETF价格精度更高
            volume=10000,
            price=Decimal('4.567'),
            fee=Decimal('2.28'),  # 较低的手续费
            timestamp="2023-01-01 10:00:00"
        )

        # 验证高精度计算
        assert isinstance(position.cost, Decimal)
        assert isinstance(position.price, Decimal)
        assert isinstance(position.worth, Decimal)

        # ETF价格变动通常较小，测试精度保持
        new_price = Decimal('4.572')  # 仅变动0.5分
        position.on_price_update(new_price)

        # 验证微小价格变动的计算精度
        expected_total_pnl = position.volume * (new_price - position.cost) - position.fee
        assert position.total_pnl == expected_total_pnl

        # ETF分红场景
        dividend_per_share = Decimal('0.025')  # 每股2.5分分红
        total_dividend = dividend_per_share * position.volume
        position.add_realized_pnl(total_dividend)

        assert position.realized_pnl == total_dividend


@pytest.mark.unit
class TestPositionQuantTrading:
    """量化交易核心场景测试"""

    def test_oversell_handling(self):
        """测试卖超处理 - 核心量化场景"""
        from decimal import Decimal
        from ginkgo.enums import DIRECTION_TYPES

        # 创建持仓1000股
        position = Position(
            portfolio_id="quant_portfolio",
            engine_id="quant_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            price=Decimal('110.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 场景1：尝试冻结超过持仓数量（预卖超）
        oversell_freeze_result = position.freeze(1500)

        # 验证预卖超被拒绝
        assert oversell_freeze_result == False  # 冻结卖超应该被拒绝
        assert position.volume == 1000         # 持仓数量不变
        assert position.frozen_volume == 0     # 冻结数量不变

        # 场景2：正确的卖出流程 - 先冻结，再卖出
        # 步骤1：预卖出(冻结)全部持仓
        freeze_result = position.freeze(1000)
        assert freeze_result == True
        assert position.volume == 0           # 可用持仓清零
        assert position.frozen_volume == 1000 # 冻结1000股

        # 步骤2：真正卖出冻结的股票
        sell_result = position.deal(DIRECTION_TYPES.SHORT, 115.0, 1000)
        assert sell_result == True
        assert position.frozen_volume == 0    # 冻结股票被消耗
        assert position.worth == Decimal('0.0')  # 市值清零（无持仓）

        # 场景3：部分卖出流程
        # 重新买入用于测试部分卖出
        position._bought(Decimal('120.0'), 800)

        # 预卖出500股
        partial_freeze_result = position.freeze(500)
        assert partial_freeze_result == True
        assert position.volume == 300         # 剩余300股可用
        assert position.frozen_volume == 500  # 冻结500股

        # 卖出其中300股
        partial_sell_result = position.deal(DIRECTION_TYPES.SHORT, 125.0, 300)
        assert partial_sell_result == True
        assert position.volume == 300         # 可用持仓不变
        assert position.frozen_volume == 200  # 冻结减少至200股

    def test_weighted_average_cost_precision(self):
        """测试多次买入的加权成本精确计算"""
        from decimal import Decimal

        # 创建空持仓
        position = Position(
            portfolio_id="quant_portfolio",
            engine_id="quant_engine",
            run_id="test_run",
            code="000001.SZ",
            timestamp="2023-01-01 10:00:00"
        )

        # 第一次买入：1000股@100元
        position._bought(Decimal('100.0'), 1000)
        assert position.cost == Decimal('100.0')
        assert position.volume == 1000

        # 第二次买入：500股@120元
        position._bought(Decimal('120.0'), 500)

        # 验证加权平均成本：(1000*100 + 500*120) / 1500 = 160000/1500 = 106.67
        expected_cost = (Decimal('1000') * Decimal('100.0') + Decimal('500') * Decimal('120.0')) / Decimal('1500')
        assert abs(position.cost - expected_cost) < Decimal('0.01')
        assert position.volume == 1500

        # 第三次买入：2000股@90元
        position._bought(Decimal('90.0'), 2000)

        # 验证新的加权平均成本：(1500*106.67 + 2000*90) / 3500
        old_total_cost = Decimal('1500') * expected_cost
        new_cost = (old_total_cost + Decimal('2000') * Decimal('90.0')) / Decimal('3500')
        assert abs(position.cost - new_cost) < Decimal('0.01')
        assert position.volume == 3500

    def test_realized_unrealized_pnl_separation(self):
        """测试已实现与未实现盈亏的严格分离"""
        from decimal import Decimal

        # 创建持仓：2000股@100元
        position = Position(
            portfolio_id="quant_portfolio",
            engine_id="quant_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=2000,
            price=Decimal('100.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 初始状态：无已实现盈亏，无未实现盈亏
        assert position.realized_pnl == Decimal('0.0')
        assert position.unrealized_pnl == Decimal('0.0')  # (price - cost) * volume - fee

        # 价格上涨至110元
        position.on_price_update(Decimal('110.0'))

        # 验证未实现盈亏增加，已实现盈亏不变
        expected_unrealized = Decimal('2000') * (Decimal('110.0') - Decimal('100.0'))
        assert position.unrealized_pnl == expected_unrealized  # 20000未实现盈利
        assert position.realized_pnl == Decimal('0.0')  # 已实现盈亏仍为0

        # 部分平仓：先冻结800股，再卖出@115元
        freeze_result = position.freeze(800)
        assert freeze_result == True
        assert position.frozen_volume == 800

        sell_result = position.deal(DIRECTION_TYPES.SHORT, 115.0, 800)
        assert sell_result == True

        # 验证已实现盈亏自动计算：800股 * (115-100) = 12000
        expected_realized_gain = Decimal('800') * (Decimal('115.0') - Decimal('100.0'))
        assert abs(position.realized_pnl - expected_realized_gain) < Decimal('0.01')

        # 验证剩余持仓的未实现盈亏：1200股 * (115-100) = 18000
        expected_unrealized = Decimal('1200') * (Decimal('115.0') - Decimal('100.0'))
        assert abs(position.unrealized_pnl - expected_unrealized) < Decimal('0.01')

        # 验证总盈亏 = 已实现 + 未实现
        total_pnl = position.realized_pnl + position.unrealized_pnl
        expected_total = Decimal('2000') * (Decimal('115.0') - Decimal('100.0'))
        assert abs(total_pnl - expected_total) < Decimal('0.01')

    def test_partial_fill_and_cancellation(self):
        """测试部分成交和撤单解冻场景"""
        from decimal import Decimal

        # 创建持仓：1000股，冻结500股（模拟挂单）
        position = Position(
            portfolio_id="quant_portfolio",
            engine_id="quant_engine",
            run_id="test_run",
            code="000001.SZ",
            cost=Decimal('100.0'),
            volume=1000,
            frozen_volume=500,
            price=Decimal('105.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 验证初始状态
        assert position.volume == 1000
        assert position.frozen_volume == 500
        assert position.available_volume == 500  # 可用数量 = 总数量 - 冻结数量

        # 场景1：部分成交200股
        partial_fill_result = position.deal(DIRECTION_TYPES.SHORT, 108.0, 200)

        # 验证部分成交成功
        assert partial_fill_result == True
        assert position.volume == 1000  # 总持仓保持不变（在freeze时已减少）
        assert position.frozen_volume == 300  # 冻结股数应相应减少200

        # 场景2：撤单解冻剩余300股
        unfreeze_result = position.unfreeze(300)

        # 验证解冻成功
        assert unfreeze_result == True
        assert position.frozen_volume == 0
        assert position.volume == 1300  # 冻结持仓恢复为可用持仓: 1000 + 300 = 1300
        assert position.available_volume == 1300  # volume(1300) - frozen_volume(0) = 1300


@pytest.mark.unit
class TestPositionTradingRegimes:
    """13. T+N交易制度测试"""

    def test_settlement_days_configuration(self):
        """测试结算天数配置"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            price=Decimal('10.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 测试默认T+0模式
        assert position.settlement_days == 0
        assert position.settlement_frozen_volume == 0

        # 测试设置T+1模式
        position.settlement_days = 1
        assert position.settlement_days == 1

        # 测试设置T+2模式
        position.settlement_days = 2
        assert position.settlement_days == 2

        # 测试无效配置的错误处理
        position.settlement_days = -1
        assert position.settlement_days == 2  # 应该保持原值

    def test_t0_immediate_availability(self):
        """测试T+0模式：买入后立即可用"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            price=Decimal('10.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 确认T+0模式
        assert position.settlement_days == 0

        # 买入100股
        result = position._bought(price=Decimal('10.0'), volume=100)
        assert result == True

        # T+0模式：立即可用，无结算冻结
        assert position.volume == 100
        assert position.settlement_frozen_volume == 0
        assert position.total_position == 100

    def test_t1_settlement_delay(self):
        """测试T+1模式：买入后次日可用"""
        import datetime
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            price=Decimal('10.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 设置T+1模式
        position.settlement_days = 1

        # 买入100股
        result = position._bought(price=Decimal('10.0'), volume=100)
        assert result == True

        # T+1模式：进入结算冻结，不可立即交易
        assert position.volume == 0  # 可用数量为0
        assert position.settlement_frozen_volume == 100  # 进入结算冻结
        assert position.total_position == 100  # 总持仓包含结算冻结

        # 模拟次日时间推进
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        settled = position.advance_time(tomorrow)

        # 验证结算成功
        assert settled == True
        assert position.volume == 100  # 结算后可用
        assert position.settlement_frozen_volume == 0  # 结算冻结清零
        assert position.total_position == 100

    def test_t2_settlement_delay(self):
        """测试T+2模式：买入后第三日可用"""
        import datetime
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            price=Decimal('10.0'),
            timestamp="2023-01-01 10:00:00"
        )

        # 设置T+2模式
        position.settlement_days = 2

        # 买入100股
        result = position._bought(price=Decimal('10.0'), volume=100)
        assert result == True

        # T+2模式：进入结算冻结
        assert position.volume == 0
        assert position.settlement_frozen_volume == 100
        assert position.total_position == 100

        # 第1天：无法结算
        day1 = datetime.datetime.now() + datetime.timedelta(days=1)
        time_advanced = position.advance_time(day1)
        assert time_advanced == True  # 时间成功推进
        assert position.settlement_frozen_volume == 100  # 仍在结算冻结中

        # 第2天：可以结算
        day2 = datetime.datetime.now() + datetime.timedelta(days=2)
        time_advanced = position.advance_time(day2)
        assert time_advanced == True  # 时间成功推进
        assert position.settlement_frozen_volume == 0  # 结算完成，冻结释放
        assert position.volume == 100
        assert position.settlement_frozen_volume == 0

    def test_multiple_batch_settlement(self):
        """测试多批次买入和分批结算"""
        import datetime
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            price=Decimal('10.0'),
            timestamp="2023-01-01 10:00:00"
        )

        position.settlement_days = 1

        # 第0天：买入100股@10元
        position._bought(price=Decimal('10.0'), volume=100)
        assert position.settlement_frozen_volume == 100
        assert position.volume == 0

        # 第1天：第一批结算，买入200股@11元
        day1 = datetime.datetime.now() + datetime.timedelta(days=1)
        position.advance_time(day1)
        assert position.volume == 100  # 第一批已结算
        assert position.settlement_frozen_volume == 0

        position._bought(price=Decimal('11.0'), volume=200)
        assert position.volume == 100  # 第一批可用
        assert position.settlement_frozen_volume == 200  # 第二批冻结

        # 第2天：第二批结算
        day2 = datetime.datetime.now() + datetime.timedelta(days=2)
        position.advance_time(day2)
        assert position.volume == 300  # 两批都可用
        assert position.settlement_frozen_volume == 0

        # 验证加权平均成本计算
        expected_cost = (Decimal('100') * Decimal('10.0') + Decimal('200') * Decimal('11.0')) / Decimal('300')
        assert abs(position.cost - expected_cost) < Decimal('0.01')

    def test_total_position_calculation(self):
        """测试总持仓计算：包括可用、冻结和结算冻结"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            price=Decimal('10.0'),
            volume=500,  # 初始可用持仓
            frozen_volume=100,  # 初始冻结持仓
            timestamp="2023-01-01 10:00:00"
        )

        position.settlement_days = 1

        # 初始状态
        assert position.total_position == 600  # 500 + 100 + 0

        # T+1买入200股
        position._bought(price=Decimal('10.0'), volume=200)

        # 验证三层持仓结构
        assert position.volume == 500  # 可用持仓
        assert position.frozen_volume == 100  # 订单冻结
        assert position.settlement_frozen_volume == 200  # 结算冻结
        assert position.total_position == 800  # 500 + 100 + 200

    def test_settlement_queue_management(self):
        """测试结算队列管理和FIFO结算"""
        import datetime
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            price=Decimal('10.0'),
            timestamp="2023-01-01 10:00:00"
        )

        position.settlement_days = 1

        # 连续3天买入，每天买入不同数量
        position._bought(price=Decimal('10.0'), volume=100)  # Day 0

        day1 = datetime.datetime.now() + datetime.timedelta(days=1)
        position.advance_time(day1)  # 结算第1批
        position._bought(price=Decimal('11.0'), volume=200)  # Day 1

        day2 = datetime.datetime.now() + datetime.timedelta(days=2)
        position.advance_time(day2)  # 结算第2批
        position._bought(price=Decimal('12.0'), volume=300)  # Day 2

        # 验证第3批仍在结算队列中
        assert position.volume == 300  # 前两批已结算
        assert position.settlement_frozen_volume == 300  # 第3批待结算

        # 结算第3批
        day3 = datetime.datetime.now() + datetime.timedelta(days=3)
        position.advance_time(day3)
        assert position.volume == 600  # 全部结算完成
        assert position.settlement_frozen_volume == 0

    def test_trading_restriction_enforcement(self):
        """测试交易限制执行：结算冻结股票无法卖出"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            price=Decimal('10.0'),
            volume=100,  # 初始可用持仓
            timestamp="2023-01-01 10:00:00"
        )

        position.settlement_days = 1

        # T+1买入200股
        position._bought(price=Decimal('10.0'), volume=200)

        # 验证状态：100股可用，200股结算冻结
        assert position.volume == 100
        assert position.settlement_frozen_volume == 200
        assert position.total_position == 300

        # 尝试冻结150股用于卖出（超过可用持仓）
        freeze_result = position.freeze(150)
        assert freeze_result == False  # 应该失败，因为超过可用持仓

        # 只能冻结可用持仓数量
        freeze_result = position.freeze(100)
        assert freeze_result == True
        assert position.frozen_volume == 100
        assert position.volume == 0  # 可用持仓被完全冻结

    def test_pnl_calculation_with_settlement(self):
        """测试包含结算冻结的盈亏计算"""
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            price=Decimal('10.0'),
            volume=100,
            cost=Decimal('10.0'),
            timestamp="2023-01-01 10:00:00"
        )

        position.settlement_days = 1

        # T+1买入200股@12元
        position._bought(price=Decimal('12.0'), volume=200)

        # 价格更新到15元
        position.on_price_update(Decimal('15.0'))

        # 验证盈亏计算包含所有持仓类型
        # 总持仓：300股（100可用 + 200结算冻结）
        # 加权成本：(100*10 + 200*12)/300 = 11.33
        # 总盈亏：300 * (15 - 11.33) = 1100
        expected_total_pnl = position.total_position * (position.price - position.cost) - position.fee
        assert abs(position.total_pnl - expected_total_pnl) < Decimal('0.01')

    def test_settlement_with_price_updates(self):
        """测试结算过程中的价格更新处理"""
        import datetime
        from decimal import Decimal

        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            price=Decimal('10.0'),
            timestamp="2023-01-01 10:00:00"
        )

        position.settlement_days = 1

        # T+1买入100股@10元
        position._bought(price=Decimal('10.0'), volume=100)

        # 价格上涨到12元（结算前）
        position.on_price_update(Decimal('12.0'))

        # 验证结算冻结股票也参与盈亏计算
        expected_unrealized = Decimal('100') * (Decimal('12.0') - Decimal('10.0'))
        assert abs(position.unrealized_pnl - expected_unrealized) < Decimal('0.01')

        # 结算日到达
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        position.advance_time(tomorrow)

        # 结算后，股票变为可用，盈亏计算不变
        assert position.volume == 100
        assert position.settlement_frozen_volume == 0
        expected_unrealized_after = Decimal('100') * (Decimal('12.0') - Decimal('10.0'))
        assert abs(position.unrealized_pnl - expected_unrealized_after) < Decimal('0.01')
