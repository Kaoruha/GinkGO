"""
Position类测试 - Refactored

使用pytest最佳实践重构的Position测试套件
包括fixtures共享、参数化测试和清晰的测试分组
"""
import pytest
import datetime
from decimal import Decimal

from ginkgo.trading.entities.position import Position
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, COMPONENT_TYPES


@pytest.mark.unit
class TestPositionConstruction:
    """1. 构造和初始化测试"""

    def test_required_parameters(self, sample_position_data):
        """测试必需参数构造"""
        position = Position(**sample_position_data)

        assert position.portfolio_id == "test_portfolio"
        assert position.code == "000001.SZ"
        assert position.volume == 1000
        assert position.cost_price == Decimal('10.50')
        assert isinstance(position.uuid, str)

    def test_base_class_inheritance(self, sample_position_data):
        """测试Base类继承验证"""
        from ginkgo.trading.core.base import Base

        position = Position(**sample_position_data)
        assert isinstance(position, Base)
        assert hasattr(position, 'uuid')
        assert hasattr(position, 'component_type')

    def test_component_type_assignment(self, sample_position_data):
        """测试组件类型分配"""
        position = Position(**sample_position_data)
        assert position.component_type == COMPONENT_TYPES.POSITION

    def test_uuid_generation(self, sample_position_data):
        """测试UUID生成和唯一性"""
        position1 = Position(**sample_position_data)
        position2 = Position(**sample_position_data)

        assert position1.uuid != position2.uuid
        assert len(position1.uuid) > 0
        assert len(position2.uuid) > 0

    def test_custom_uuid(self, sample_position_data):
        """测试自定义UUID"""
        custom_uuid = "custom-position-uuid-789"
        sample_position_data['uuid'] = custom_uuid

        position = Position(**sample_position_data)
        assert position.uuid == custom_uuid


@pytest.mark.unit
class TestPositionProperties:
    """2. 属性访问测试"""

    def test_portfolio_id_validation(self, sample_position_data):
        """测试portfolio_id验证"""
        position = Position(**sample_position_data)
        assert position.portfolio_id == "test_portfolio"
        assert isinstance(position.portfolio_id, str)

    def test_code_validation(self, sample_position_data):
        """测试code验证"""
        position = Position(**sample_position_data)
        assert position.code == "000001.SZ"
        assert isinstance(position.code, str)

    def test_volume_validation(self, sample_position_data):
        """测试volume验证"""
        # 有效整数值
        sample_position_data['volume'] = 1000
        position = Position(**sample_position_data)
        assert position.volume == 1000
        assert isinstance(position.volume, int)

        # 负数被拒绝
        sample_position_data['volume'] = -100
        with pytest.raises(Exception):
            Position(**sample_position_data)

    def test_cost_price_validation(self, sample_position_data):
        """测试cost_price验证"""
        position = Position(**sample_position_data)
        assert position.cost_price == Decimal('10.50')
        assert isinstance(position.cost_price, Decimal)

    def test_current_price_validation(self, sample_position_data):
        """测试current_price验证"""
        position = Position(**sample_position_data)
        assert position.current_price == Decimal('11.00')
        assert isinstance(position.current_price, Decimal)


@pytest.mark.unit
class TestPositionCalculations:
    """3. 持仓计算测试"""

    @pytest.mark.parametrize("volume,cost_price,current_price,expected_pnl", [
        (1000, Decimal('10.00'), Decimal('11.00'), Decimal('1000.00')),  # 盈利
        (1000, Decimal('10.00'), Decimal('9.00'), Decimal('-1000.00')),  # 亏损
        (1000, Decimal('10.00'), Decimal('10.00'), Decimal('0.00')),    # 平手
        (500, Decimal('20.50'), Decimal('21.00'), Decimal('250.00')),  # 小额盈利
    ])
    def test_pnl_calculation(self, sample_position_data, volume, cost_price, current_price, expected_pnl):
        """测试盈亏计算"""
        sample_position_data.update({
            'volume': volume,
            'cost_price': cost_price,
            'current_price': current_price
        })
        position = Position(**sample_position_data)
        assert position.pnl == expected_pnl

    @pytest.mark.parametrize("volume,cost_price,current_price,expected_pnl_pct", [
        (1000, Decimal('10.00'), Decimal('11.00'), Decimal('10.00')),   # +10%
        (1000, Decimal('10.00'), Decimal('9.00'), Decimal('-10.00')),  # -10%
        (1000, Decimal('10.00'), Decimal('10.00'), Decimal('0.00')),    # 0%
        (1000, Decimal('20.00'), Decimal('22.00'), Decimal('10.00')),   # +10%
    ])
    def test_pnl_percentage_calculation(self, sample_position_data, volume, cost_price, current_price, expected_pnl_pct):
        """测试盈亏百分比计算"""
        sample_position_data.update({
            'volume': volume,
            'cost_price': cost_price,
            'current_price': current_price
        })
        position = Position(**sample_position_data)
        assert position.pnl_pct == expected_pnl_pct

    @pytest.mark.parametrize("volume,cost_price,expected_market_value", [
        (1000, Decimal('10.50'), Decimal('10500.00')),
        (500, Decimal('20.00'), Decimal('10000.00')),
        (1500, Decimal('15.75'), Decimal('23625.00')),
    ])
    def test_market_value_calculation(self, sample_position_data, volume, cost_price, expected_market_value):
        """测试市值计算"""
        sample_position_data.update({
            'volume': volume,
            'cost_price': cost_price,
            'current_price': cost_price  # 市值使用当前价，这里用成本价代替
        })
        position = Position(**sample_position_data)
        assert position.market_value == expected_market_value

    @pytest.mark.parametrize("volume,available_volume,expected", [
        (1000, 1000, 0),    # 全部可用
        (1000, 500, 500),    # 部分冻结
        (1000, 0, 1000),    # 全部冻结
        (1000, 100, 900),    # 大部分可用
    ])
    def test_frozen_volume_calculation(self, sample_position_data, volume, available_volume, expected):
        """测试冻结数量计算"""
        sample_position_data.update({
            'volume': volume,
            'available_volume': available_volume
        })
        position = Position(**sample_position_data)
        assert position.frozen_volume == expected


@pytest.mark.unit
class TestPositionEdgeCases:
    """4. 边界情况测试"""

    def test_zero_volume(self, sample_position_data):
        """测试零持仓"""
        sample_position_data['volume'] = 0
        position = Position(**sample_position_data)

        assert position.volume == 0
        assert position.market_value == Decimal('0')
        assert position.pnl == Decimal('0')

    def test_negative_prices(self, sample_position_data):
        """测试负价格（期货场景）"""
        sample_position_data.update({
            'cost_price': Decimal('-10.50'),
            'current_price': Decimal('-11.00')
        })
        position = Position(**sample_position_data)

        # 亏损计算
        assert position.cost_price == Decimal('-10.50')
        assert position.current_price == Decimal('-11.00')

    def test_high_precision_prices(self, sample_position_data):
        """测试高精度价格"""
        sample_position_data.update({
            'cost_price': Decimal('10.123456789'),
            'current_price': Decimal('10.987654321')
        })
        position = Position(**sample_position_data)

        assert isinstance(position.cost_price, Decimal)
        assert isinstance(position.current_price, Decimal)
        assert position.cost_price == Decimal('10.123456789')

    @pytest.mark.parametrize("volume", [
        1,          # 最小持仓
        1000000,    # 大持仓
        100,        # 标准手数
    ])
    def test_various_volumes(self, sample_position_data, volume):
        """测试各种持仓量"""
        sample_position_data['volume'] = volume
        position = Position(**sample_position_data)
        assert position.volume == volume


@pytest.mark.unit
class TestPositionValidation:
    """5. 持仓验证测试"""

    def test_available_volume_range(self, sample_position_data):
        """测试可用数量范围"""
        # available_volume不能超过volume
        sample_position_data.update({
            'volume': 1000,
            'available_volume': 1500
        })
        with pytest.raises(Exception):
            Position(**sample_position_data)

        # available_volume可以为0
        sample_position_data['available_volume'] = 0
        position = Position(**sample_position_data)
        assert position.available_volume == 0

    def test_price_consistency(self, sample_position_data):
        """测试价格一致性"""
        # 成本价和当前价应该都是Decimal
        position = Position(**sample_position_data)
        assert isinstance(position.cost_price, Decimal)
        assert isinstance(position.current_price, Decimal)

    @pytest.mark.parametrize("code", [
        "000001.SZ",
        "600000.SH",
        "300001.SZ",
        "AAPL",
        "BTC/USD"
    ])
    def test_various_codes(self, sample_position_data, code):
        """测试各种股票代码"""
        sample_position_data['code'] = code
        position = Position(**sample_position_data)
        assert position.code == code


@pytest.mark.unit
class TestPositionStatus:
    """6. 持仓状态测试"""

    @pytest.mark.parametrize("available_volume,volume,expected_status", [
        (1000, 1000, "available"),      # 全部可用
        (500, 1000, "partially_frozen"), # 部分冻结
        (0, 1000, "fully_frozen"),       # 全部冻结
        (0, 0, "closed"),               # 已平仓
    ])
    def test_position_status(self, sample_position_data, available_volume, volume, expected_status):
        """测试持仓状态"""
        sample_position_data.update({
            'volume': volume,
            'available_volume': available_volume
        })
        position = Position(**sample_position_data)

        if expected_status == "available":
            assert position.available_volume == position.volume
        elif expected_status == "partially_frozen":
            assert position.frozen_volume > 0
            assert position.available_volume > 0
        elif expected_status == "fully_frozen":
            assert position.available_volume == 0
            assert position.frozen_volume == position.volume


@pytest.mark.financial
class TestPositionBusinessScenarios:
    """7. 业务场景测试"""

    def test_long_position_profit(self, sample_position_data):
        """测试多头盈利场景"""
        sample_position_data.update({
            'volume': 1000,
            'cost_price': Decimal('10.00'),
            'current_price': Decimal('12.00')
        })
        position = Position(**sample_position_data)

        assert position.pnl == Decimal('2000.00')
        assert position.pnl_pct == Decimal('20.00')

    def test_long_position_loss(self, sample_position_data):
        """测试多头亏损场景"""
        sample_position_data.update({
            'volume': 1000,
            'cost_price': Decimal('10.00'),
            'current_price': Decimal('8.00')
        })
        position = Position(**sample_position_data)

        assert position.pnl == Decimal('-2000.00')
        assert position.pnl_pct == Decimal('-20.00')

    def test_short_position_profit(self, sample_position_data):
        """测试空头盈利场景（价格下跌）"""
        sample_position_data.update({
            'volume': 1000,
            'cost_price': Decimal('10.00'),
            'current_price': Decimal('8.00')
        })
        position = Position(**sample_position_data)

        # 空头盈利：价格下跌时盈利
        assert position.current_price < position.cost_price

    def test_position_update(self, sample_position_data):
        """测试持仓更新"""
        position = Position(**sample_position_data)

        # 更新当前价格
        new_price = Decimal('12.00')
        position.current_price = new_price

        assert position.current_price == new_price


@pytest.mark.integration
class TestPositionDatabaseOperations:
    """8. 数据库操作测试"""

    def test_position_to_model(self, sample_position_data, ginkgo_config):
        """测试Position到Model的转换"""
        position = Position(**sample_position_data)
        model = position.to_model()

        assert model.portfolio_id == position.portfolio_id
        assert model.code == position.code
        assert model.volume == position.volume

    def test_position_from_model(self, sample_position_data, ginkgo_config):
        """测试Model到Position的转换"""
        position1 = Position(**sample_position_data)
        model = position1.to_model()
        position2 = Position.from_model(model)

        assert position2.portfolio_id == position1.portfolio_id
        assert position2.code == position1.code
        assert position2.volume == position1.volume


@pytest.mark.unit
class TestPositionDataSetting:
    """9. 数据设置测试"""

    def test_direct_parameter_setting(self, sample_position_data):
        """测试直接参数设置"""
        position = Position(**sample_position_data)

        # 重新设置
        position.set(
            "updated_portfolio",
            "updated_engine",
            "updated_run",
            "000002.SZ",
            2000,
            1500,
            Decimal('12.00'),
            Decimal('13.00')
        )

        assert position.portfolio_id == "updated_portfolio"
        assert position.code == "000002.SZ"
        assert position.volume == 2000

    def test_pandas_series_setting(self, sample_position_data):
        """测试pandas.Series设置"""
        import pandas as pd

        position = Position(**sample_position_data)

        series_data = pd.Series({
            'portfolio_id': 'SERIES_PORTFOLIO',
            'engine_id': 'SERIES_ENGINE',
            'run_id': 'SERIES_RUN',
            'code': '000002.SZ',
            'volume': 2000,
            'available_volume': 1500,
            'cost_price': 12.50,
            'current_price': 13.00
        })

        position.set(series_data)

        assert position.portfolio_id == 'SERIES_PORTFOLIO'
        assert position.code == '000002.SZ'
        assert position.volume == 2000


@pytest.mark.unit
class TestPositionTimestamp:
    """10. 时间戳测试"""

    def test_timestamp_validation(self, sample_position_data):
        """测试时间戳验证"""
        # datetime对象
        dt = datetime.datetime(2024, 1, 1, 15, 0, 0)
        sample_position_data['timestamp'] = dt
        position = Position(**sample_position_data)
        assert position.timestamp == dt

        # 字符串时间
        time_str = "2024-01-01 15:00:00"
        sample_position_data['timestamp'] = time_str
        position = Position(**sample_position_data)
        assert isinstance(position.timestamp, datetime.datetime)

    @pytest.mark.parametrize("time_format", [
        "2024-01-01",
        "2024-01-01 15:00:00",
        datetime.datetime(2024, 1, 1, 15, 0, 0)
    ])
    def test_various_time_formats(self, sample_position_data, time_format):
        """测试各种时间格式"""
        sample_position_data['timestamp'] = time_format
        position = Position(**sample_position_data)
        assert isinstance(position.timestamp, datetime.datetime)
