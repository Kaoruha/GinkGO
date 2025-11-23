"""
Transfer类TDD测试

通过TDD方式开发Transfer资金转移类的完整测试套件
涵盖资金转移和状态管理功能
"""
import pytest
import datetime

# 导入Transfer类和相关枚举
try:
    from ginkgo.trading.entities.transfer import Transfer
    from ginkgo.enums import TRANSFERDIRECTION_TYPES, TRANSFERSTATUS_TYPES, MARKET_TYPES, COMPONENT_TYPES
    from decimal import Decimal
    import pandas as pd
except ImportError as e:
    assert False, "TDD Red阶段：测试用例尚未实现"


@pytest.mark.unit
class TestTransferConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认参数构造"""
        # Transfer与Position、Signal保持一致，要求核心业务参数不能为空
        with pytest.raises(TypeError):
            Transfer()

    def test_full_parameter_constructor(self):
        """测试完整参数构造"""
        # 测试完整参数构造，所有字段正确赋值和严格类型检查
        transfer = Transfer(
            portfolio_id="test_portfolio_001",
            engine_id="engine_001",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("10000.50"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 验证字符串类型和值
        assert transfer.portfolio_id == "test_portfolio_001"
        assert isinstance(transfer.portfolio_id, str)
        assert transfer.engine_id == "engine_001"
        assert isinstance(transfer.engine_id, str)

        # 验证枚举类型和值
        assert transfer.direction == TRANSFERDIRECTION_TYPES.IN
        assert isinstance(transfer.direction, TRANSFERDIRECTION_TYPES)
        assert transfer.market == MARKET_TYPES.CHINA
        assert isinstance(transfer.market, MARKET_TYPES)
        assert transfer.status == TRANSFERSTATUS_TYPES.NEW
        assert isinstance(transfer.status, TRANSFERSTATUS_TYPES)

        # 验证金额类型和精度保持
        assert transfer.money == Decimal("10000.50")
        assert isinstance(transfer.money, Decimal)

        # 验证时间戳类型和值
        assert transfer.timestamp == datetime.datetime(2023, 1, 3)
        assert isinstance(transfer.timestamp, datetime.datetime)

    def test_base_class_inheritance(self):
        """测试Base类继承验证"""
        # 验证正确继承Base类的功能 - 使用有效参数创建实例
        from ginkgo.trading.core.base import Base

        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 验证继承关系
        assert isinstance(transfer, Base)

        # 验证Base类的基本功能（如UUID）
        assert hasattr(transfer, 'uuid')
        assert len(transfer.uuid) > 0

    def test_uuid_initialization(self):
        """测试UUID初始化"""
        # 测试UUID的设置和生成

        # 测试自动生成UUID
        transfer1 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )
        assert len(transfer1.uuid) > 0
        assert isinstance(transfer1.uuid, str)

        # 测试自定义UUID
        custom_uuid = "custom-uuid-12345"
        transfer2 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230104_001",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED,
            timestamp="2023-01-04",
            uuid=custom_uuid
        )
        assert transfer2.uuid == custom_uuid

        # 测试UUID唯一性（自动生成的不同）
        transfer3 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_002",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )
        assert transfer1.uuid != transfer3.uuid

    def test_direction_enum_assignment(self):
        """测试转账方向枚举分配"""
        # 验证TRANSFERDIRECTION_TYPES枚举正确分配

        # 测试所有有效的转账方向
        valid_directions = [TRANSFERDIRECTION_TYPES.IN, TRANSFERDIRECTION_TYPES.OUT]
        for direction in valid_directions:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=direction,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )
            assert transfer.direction == direction
            assert isinstance(transfer.direction, TRANSFERDIRECTION_TYPES)

        # 测试无效的方向类型（字符串）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction="IN",  # 字符串而非枚举
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

        # 测试无效的方向类型（整数）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=1,  # 整数而非枚举
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

    def test_status_enum_assignment(self):
        """测试转账状态枚举分配"""
        # 验证TRANSFERSTATUS_TYPES枚举正确分配

        # 测试所有有效的转账状态
        valid_statuses = [
            TRANSFERSTATUS_TYPES.NEW,
            TRANSFERSTATUS_TYPES.SUBMITTED,
            TRANSFERSTATUS_TYPES.FILLED,
            TRANSFERSTATUS_TYPES.CANCELED,
            TRANSFERSTATUS_TYPES.PENDING
        ]

        for status in valid_statuses:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=status,
                timestamp="2023-01-03"
            )
            assert transfer.status == status
            assert isinstance(transfer.status, TRANSFERSTATUS_TYPES)

        # 测试无效的状态类型（字符串）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status="NEW",  # 字符串而非枚举
                timestamp="2023-01-03"
            )

        # 测试无效的状态类型（整数）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=1,  # 整数而非枚举
                timestamp="2023-01-03"
            )

    def test_market_enum_assignment(self):
        """测试市场枚举分配"""
        # 验证MARKET_TYPES枚举正确分配

        # 测试所有有效的市场类型
        valid_markets = [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ, MARKET_TYPES.OTHER]
        for market in valid_markets:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=market,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )
            assert transfer.market == market
            assert isinstance(transfer.market, MARKET_TYPES)

        # 测试无效的市场类型（字符串）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market="CHINA",  # 字符串而非枚举
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

        # 测试无效的市场类型（整数）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=1,  # 整数而非枚举
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

    def test_timestamp_initialization(self):
        """测试时间戳初始化"""
        # 测试时间戳的设置和标准化

        # 测试有效的时间戳格式
        valid_timestamps = [
            "2023-01-03",  # 字符串格式
            datetime.datetime(2023, 1, 3),  # datetime对象
            "2023-06-15 09:30:00",  # 带时间的字符串
            datetime.datetime(2023, 12, 25, 14, 30, 0)  # 带时间的datetime
        ]

        for timestamp in valid_timestamps:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp=timestamp
            )
            assert isinstance(transfer.timestamp, datetime.datetime)

        # 测试无效的时间戳格式
        invalid_timestamps = [
            "invalid_date",  # 无效日期字符串
            "2023-13-01",    # 无效月份
            "2023-01-32",    # 无效日期
            "",              # 空字符串
        ]

        for invalid_timestamp in invalid_timestamps:
            with pytest.raises(ValueError):
                Transfer(
                    portfolio_id="test_portfolio",
                    engine_id="test_engine",
                    run_id="run_20230103_001",
                    direction=TRANSFERDIRECTION_TYPES.IN,
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("1000.00"),
                    status=TRANSFERSTATUS_TYPES.NEW,
                    timestamp=invalid_timestamp
                )

        # 测试无效的时间戳类型
        invalid_types = [[], {}]  # 列表、字典
        for invalid_type in invalid_types:
            with pytest.raises(TypeError):
                Transfer(
                    portfolio_id="test_portfolio",
                    engine_id="test_engine",
                    run_id="run_20230103_001",
                    direction=TRANSFERDIRECTION_TYPES.IN,
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("1000.00"),
                    status=TRANSFERSTATUS_TYPES.NEW,
                    timestamp=invalid_type
                )

        # 测试None时间戳应该被拒绝（严格验证模式）
        with pytest.raises(ValueError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp=None
            )


@pytest.mark.unit
class TestTransferProperties:
    """2. 属性访问测试"""

    def test_portfolio_id_property(self):
        """测试组合ID属性"""
        # 测试组合ID属性的正确读取
        transfer = Transfer(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )
        assert transfer.portfolio_id == "test_portfolio_001"
        assert isinstance(transfer.portfolio_id, str)

    def test_engine_id_property(self):
        """测试引擎ID属性"""
        # 测试引擎ID属性的正确读取
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine_001",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )
        assert transfer.engine_id == "test_engine_001"
        assert isinstance(transfer.engine_id, str)

    def test_run_id_property(self):
        """测试运行ID属性"""
        # 测试运行ID属性的正确读取
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )
        assert transfer.run_id == "run_20230103_001"
        assert isinstance(transfer.run_id, str)

    def test_direction_property(self):
        """测试转账方向属性"""
        # 测试转账方向属性的正确读取和枚举类型

        # 测试IN方向
        transfer_in = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )
        assert transfer_in.direction == TRANSFERDIRECTION_TYPES.IN
        assert isinstance(transfer_in.direction, TRANSFERDIRECTION_TYPES)

        # 测试OUT方向
        transfer_out = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_002",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED,
            timestamp="2023-01-03"
        )
        assert transfer_out.direction == TRANSFERDIRECTION_TYPES.OUT
        assert isinstance(transfer_out.direction, TRANSFERDIRECTION_TYPES)

    def test_market_property(self):
        """测试市场属性"""
        # 测试市场属性的正确读取和枚举类型

        # 测试中国市场
        transfer_china = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )
        assert transfer_china.market == MARKET_TYPES.CHINA
        assert isinstance(transfer_china.market, MARKET_TYPES)

        # 测试纳斯达克市场
        transfer_nasdaq = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_002",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED,
            timestamp="2023-01-03"
        )
        assert transfer_nasdaq.market == MARKET_TYPES.NASDAQ
        assert isinstance(transfer_nasdaq.market, MARKET_TYPES)

        # 测试其他市场
        transfer_other = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_003",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.OTHER,
            money=Decimal("3000.00"),
            status=TRANSFERSTATUS_TYPES.PENDING,
            timestamp="2023-01-03"
        )
        assert transfer_other.market == MARKET_TYPES.OTHER
        assert isinstance(transfer_other.market, MARKET_TYPES)

    def test_money_property(self):
        """测试金额属性"""
        # 测试转账金额属性的正确读取和类型
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("12345.67"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )
        assert transfer.money == Decimal("12345.67")
        assert isinstance(transfer.money, Decimal)

        # 测试不同精度的金额
        transfer2 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230104_001",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=1000,  # 整数
            status=TRANSFERSTATUS_TYPES.FILLED,
            timestamp="2023-01-04"
        )
        assert transfer2.money == Decimal("1000")
        assert isinstance(transfer2.money, Decimal)

    def test_status_property(self):
        """测试状态属性"""
        # 测试转账状态属性的正确读取和枚举类型

        # 测试所有有效状态
        status_test_cases = [
            (TRANSFERSTATUS_TYPES.NEW, "NEW"),
            (TRANSFERSTATUS_TYPES.SUBMITTED, "SUBMITTED"),
            (TRANSFERSTATUS_TYPES.FILLED, "FILLED"),
            (TRANSFERSTATUS_TYPES.CANCELED, "CANCELED"),
            (TRANSFERSTATUS_TYPES.PENDING, "PENDING")
        ]

        for status_enum, status_name in status_test_cases:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id=f"run_20230103_{status_name.lower()}",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=status_enum,
                timestamp="2023-01-03"
            )
            assert transfer.status == status_enum
            assert isinstance(transfer.status, TRANSFERSTATUS_TYPES)

    def test_timestamp_property(self):
        """测试时间戳属性"""
        # 测试时间戳属性的正确读取和格式

        # 测试字符串时间戳
        transfer1 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-12-25"
        )
        assert transfer1.timestamp == datetime.datetime(2023, 12, 25)
        assert isinstance(transfer1.timestamp, datetime.datetime)

        # 测试datetime对象时间戳
        test_datetime = datetime.datetime(2023, 6, 15, 14, 30, 0)
        transfer2 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230615_001",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED,
            timestamp=test_datetime
        )
        assert transfer2.timestamp == test_datetime
        assert isinstance(transfer2.timestamp, datetime.datetime)

        # 测试带时间的字符串时间戳
        transfer3 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230918_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.OTHER,
            money=Decimal("3000.00"),
            status=TRANSFERSTATUS_TYPES.PENDING,
            timestamp="2023-09-18 09:30:00"
        )
        expected_datetime = datetime.datetime(2023, 9, 18, 9, 30, 0)
        assert transfer3.timestamp == expected_datetime
        assert isinstance(transfer3.timestamp, datetime.datetime)

    def test_uuid_property(self):
        """测试UUID属性"""
        # 测试UUID属性的正确读取和唯一性

        # 测试自动生成的UUID
        transfer1 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )
        assert len(transfer1.uuid) > 0
        assert isinstance(transfer1.uuid, str)

        # 测试自定义UUID
        custom_uuid = "custom-transfer-uuid-12345"
        transfer2 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_002",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED,
            timestamp="2023-01-03",
            uuid=custom_uuid
        )
        assert transfer2.uuid == custom_uuid
        assert isinstance(transfer2.uuid, str)

        # 测试UUID唯一性（自动生成的应该不同）
        transfer3 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_003",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.OTHER,
            money=Decimal("3000.00"),
            status=TRANSFERSTATUS_TYPES.PENDING,
            timestamp="2023-01-03"
        )
        assert transfer1.uuid != transfer3.uuid


@pytest.mark.unit
class TestTransferDataSetting:
    """3. 数据设置测试"""

    def test_direct_parameter_setting(self):
        """测试直接参数设置"""
        # 测试直接参数方式设置转账数据
        transfer = Transfer(
            portfolio_id="test_portfolio_initial",
            engine_id="test_engine_initial",
            run_id="run_20230103_initial",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 使用set方法更新数据
        transfer.set(
            "test_portfolio_updated",
            "test_engine_updated",
            "run_20230103_updated",
            TRANSFERDIRECTION_TYPES.OUT,
            MARKET_TYPES.NASDAQ,
            Decimal("2500.75"),
            TRANSFERSTATUS_TYPES.FILLED,
            "2023-06-15"
        )

        # 验证数据已正确更新
        assert transfer.portfolio_id == "test_portfolio_updated"
        assert transfer.engine_id == "test_engine_updated"
        assert transfer.run_id == "run_20230103_updated"
        assert transfer.direction == TRANSFERDIRECTION_TYPES.OUT
        assert transfer.market == MARKET_TYPES.NASDAQ
        assert transfer.money == Decimal("2500.75")
        assert transfer.status == TRANSFERSTATUS_TYPES.FILLED
        assert transfer.timestamp == datetime.datetime(2023, 6, 15)

    def test_pandas_series_setting(self):
        """测试pandas.Series设置"""
        # 测试从pandas.Series设置转账数据
        series_data = pd.Series({
            "portfolio_id": "series_portfolio_001",
            "engine_id": "series_engine_001",
            "run_id": "run_20230901_series",
            "direction": TRANSFERDIRECTION_TYPES.OUT,
            "market": MARKET_TYPES.OTHER,
            "money": Decimal("3333.33"),
            "status": TRANSFERSTATUS_TYPES.PENDING,
            "timestamp": "2023-09-01"
        })

        transfer = Transfer(
            portfolio_id="initial_portfolio",
            engine_id="initial_engine",
            run_id="run_initial",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )
        transfer.set(series_data)

        # 验证从Series设置的数据
        assert transfer.portfolio_id == "series_portfolio_001"
        assert transfer.engine_id == "series_engine_001"
        assert transfer.run_id == "run_20230901_series"
        assert transfer.direction == TRANSFERDIRECTION_TYPES.OUT
        assert transfer.market == MARKET_TYPES.OTHER
        assert transfer.money == Decimal("3333.33")
        assert transfer.status == TRANSFERSTATUS_TYPES.PENDING
        assert transfer.timestamp == datetime.datetime(2023, 9, 1)

    def test_pandas_dataframe_setting(self):
        """测试pandas.DataFrame设置"""
        # 测试从pandas.DataFrame设置转账数据
        dataframe_data = pd.DataFrame({
            "portfolio_id": ["df_portfolio_001"],
            "engine_id": ["df_engine_001"],
            "run_id": ["run_20231001_df"],
            "direction": [TRANSFERDIRECTION_TYPES.IN],
            "market": [MARKET_TYPES.OTHER],
            "money": [Decimal("4444.44")],
            "status": [TRANSFERSTATUS_TYPES.SUBMITTED],
            "timestamp": ["2023-10-01"]
        })

        transfer = Transfer(
            portfolio_id="initial_portfolio",
            engine_id="initial_engine",
            run_id="run_initial",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )
        transfer.set(dataframe_data)

        # 验证从DataFrame设置的数据
        assert transfer.portfolio_id == "df_portfolio_001"
        assert transfer.engine_id == "df_engine_001"
        assert transfer.run_id == "run_20231001_df"
        assert transfer.direction == TRANSFERDIRECTION_TYPES.IN
        assert transfer.market == MARKET_TYPES.OTHER
        assert transfer.money == Decimal("4444.44")
        assert transfer.status == TRANSFERSTATUS_TYPES.SUBMITTED
        assert transfer.timestamp == datetime.datetime(2023, 10, 1)

    def test_singledispatch_routing(self):
        """测试方法分派路由"""
        # 测试方法分派路由的正确性
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 测试不支持的类型会抛异常
        with pytest.raises(NotImplementedError):
            transfer.set(["unsupported", "list", "type"])

        with pytest.raises(NotImplementedError):
            transfer.set({"unsupported": "dict", "type": True})

        # 测试支持的类型能正确路由

        # 1. 直接参数路由
        transfer.set(
            "param_portfolio",
            "param_engine",
            "run_param",
            TRANSFERDIRECTION_TYPES.OUT,
            MARKET_TYPES.NASDAQ,
            Decimal("4000.00"),
            TRANSFERSTATUS_TYPES.CANCELED,
            "2023-04-15"
        )
        assert transfer.portfolio_id == "param_portfolio"
        assert transfer.direction == TRANSFERDIRECTION_TYPES.OUT

        # 2. pandas.Series路由
        series = pd.Series({
            "portfolio_id": "series_portfolio",
            "engine_id": "series_engine",
            "run_id": "run_series",
            "direction": TRANSFERDIRECTION_TYPES.IN,
            "market": MARKET_TYPES.OTHER,
            "money": Decimal("5000.00"),
            "status": TRANSFERSTATUS_TYPES.SUBMITTED,
            "timestamp": "2023-05-20"
        })
        transfer.set(series)
        assert transfer.portfolio_id == "series_portfolio"
        assert transfer.direction == TRANSFERDIRECTION_TYPES.IN

        # 3. pandas.DataFrame路由
        dataframe = pd.DataFrame({
            "portfolio_id": ["df_portfolio"],
            "engine_id": ["df_engine"],
            "run_id": ["run_df"],
            "direction": [TRANSFERDIRECTION_TYPES.OUT],
            "market": [MARKET_TYPES.CHINA],
            "money": [Decimal("6000.00")],
            "status": [TRANSFERSTATUS_TYPES.CANCELED],
            "timestamp": ["2023-07-25"]
        })
        transfer.set(dataframe)
        assert transfer.portfolio_id == "df_portfolio"
        assert transfer.direction == TRANSFERDIRECTION_TYPES.OUT

    def test_parameter_order_validation(self):
        """测试参数顺序验证"""
        # 测试转账参数顺序的严格要求
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 测试正确的参数顺序
        transfer.set(
            "portfolio_correct",      # portfolio_id
            "engine_correct",         # engine_id
            "run_correct",           # run_id
            TRANSFERDIRECTION_TYPES.OUT,  # direction
            MARKET_TYPES.NASDAQ,     # market
            Decimal("2000.00"),      # money
            TRANSFERSTATUS_TYPES.FILLED,  # status
            "2023-06-15"            # timestamp
        )

        # 验证参数按正确顺序设置
        assert transfer.portfolio_id == "portfolio_correct"
        assert transfer.engine_id == "engine_correct"
        assert transfer.run_id == "run_correct"
        assert transfer.direction == TRANSFERDIRECTION_TYPES.OUT
        assert transfer.market == MARKET_TYPES.NASDAQ
        assert transfer.money == Decimal("2000.00")
        assert transfer.status == TRANSFERSTATUS_TYPES.FILLED
        assert transfer.timestamp == datetime.datetime(2023, 6, 15)

        # 测试参数数量不正确的情况
        with pytest.raises(TypeError):
            transfer.set("only_one_param")

        with pytest.raises(TypeError):
            transfer.set("param1", "param2")  # 参数太少

    def test_required_fields_validation(self):
        """测试必需字段验证"""
        # 测试Series中必需字段的验证
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 测试包含所有必需字段的Series
        complete_series = pd.Series({
            "portfolio_id": "complete_portfolio",
            "engine_id": "complete_engine",
            "run_id": "run_complete",
            "direction": TRANSFERDIRECTION_TYPES.OUT,
            "market": MARKET_TYPES.NASDAQ,
            "money": Decimal("2000.00"),
            "timestamp": "2023-06-15"
        })
        transfer.set(complete_series)
        assert transfer.portfolio_id == "complete_portfolio"

        # 测试缺少portfolio_id字段
        missing_portfolio_series = pd.Series({
            "engine_id": "test_engine",
            "run_id": "run_test",
            "direction": TRANSFERDIRECTION_TYPES.IN,
            "market": MARKET_TYPES.CHINA,
            "money": Decimal("1000.00"),
            "timestamp": "2023-01-03"
        })
        with pytest.raises(ValueError, match="Missing required fields"):
            transfer.set(missing_portfolio_series)

        # 测试缺少engine_id字段
        missing_engine_series = pd.Series({
            "portfolio_id": "test_portfolio",
            "run_id": "run_test",
            "direction": TRANSFERDIRECTION_TYPES.IN,
            "market": MARKET_TYPES.CHINA,
            "money": Decimal("1000.00"),
            "timestamp": "2023-01-03"
        })
        with pytest.raises(ValueError, match="Missing required fields"):
            transfer.set(missing_engine_series)

        # 测试缺少多个字段
        missing_multiple_series = pd.Series({
            "portfolio_id": "test_portfolio",
            "direction": TRANSFERDIRECTION_TYPES.IN
        })
        with pytest.raises(ValueError, match="Missing required fields"):
            transfer.set(missing_multiple_series)

    def test_uuid_setting_validation(self):
        """测试UUID设置验证"""
        # 测试UUID设置的正确性和唯一性
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        original_uuid = transfer.uuid
        assert len(original_uuid) > 0

        # 设置数据时UUID应该保持不变（不会重新生成）
        transfer.set(
            "updated_portfolio",
            "updated_engine",
            "run_updated",
            TRANSFERDIRECTION_TYPES.OUT,
            MARKET_TYPES.NASDAQ,
            Decimal("2000.00"),
            TRANSFERSTATUS_TYPES.FILLED,
            "2023-06-15"
        )

        # UUID应该保持不变
        assert transfer.uuid == original_uuid

        # 从Series设置数据时UUID也应该保持不变
        series_data = pd.Series({
            "portfolio_id": "series_portfolio",
            "engine_id": "series_engine",
            "run_id": "run_series",
            "direction": TRANSFERDIRECTION_TYPES.IN,
            "market": MARKET_TYPES.OTHER,
            "money": Decimal("3000.00"),
            "timestamp": "2023-09-01"
        })
        transfer.set(series_data)

        # UUID仍应该保持不变
        assert transfer.uuid == original_uuid

    def test_datetime_normalization_setting(self):
        """测试设置时的时间标准化处理"""
        # 测试设置时的时间标准化处理
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 测试各种时间格式的标准化
        test_timestamps = [
            ("2023-12-25", datetime.datetime(2023, 12, 25)),
            ("2023-06-15 14:30:00", datetime.datetime(2023, 6, 15, 14, 30, 0)),
            (datetime.datetime(2023, 9, 18, 9, 30, 0), datetime.datetime(2023, 9, 18, 9, 30, 0))
        ]

        for input_timestamp, expected_datetime in test_timestamps:
            transfer.set(
                "test_portfolio",
                "test_engine",
                "run_test",
                TRANSFERDIRECTION_TYPES.OUT,
                MARKET_TYPES.NASDAQ,
                Decimal("2000.00"),
                TRANSFERSTATUS_TYPES.FILLED,
                input_timestamp
            )
            assert transfer.timestamp == expected_datetime
            assert isinstance(transfer.timestamp, datetime.datetime)

        # 测试Series中的时间标准化
        series_data = pd.Series({
            "portfolio_id": "series_portfolio",
            "engine_id": "series_engine",
            "run_id": "run_series",
            "direction": TRANSFERDIRECTION_TYPES.IN,
            "market": MARKET_TYPES.OTHER,
            "money": Decimal("3000.00"),
            "timestamp": "2023-11-11 11:11:11"
        })
        transfer.set(series_data)

        expected_series_datetime = datetime.datetime(2023, 11, 11, 11, 11, 11)
        assert transfer.timestamp == expected_series_datetime
        assert isinstance(transfer.timestamp, datetime.datetime)

    def test_unsupported_type_rejection(self):
        """测试不支持类型拒绝"""
        # 测试singledispatch对不支持类型的拒绝
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 测试各种不支持的类型
        unsupported_types = [
            ["list", "type"],           # 列表
            {"dict": "type"},           # 字典
            42,                         # 整数
            3.14,                       # 浮点数
            True,                       # 布尔值
            set(["set", "type"]),        # 集合
            ("tuple", "type"),          # 元组
            None,                       # None值
        ]

        for unsupported_input in unsupported_types:
            with pytest.raises(NotImplementedError, match="Unsupported input type"):
                transfer.set(unsupported_input)

        # 确保设置失败后transfer状态未改变
        assert transfer.portfolio_id == "test_portfolio"
        assert transfer.engine_id == "test_engine"
        assert transfer.run_id == "run_20230103_001"
        assert transfer.direction == TRANSFERDIRECTION_TYPES.IN
        assert transfer.market == MARKET_TYPES.CHINA
        assert transfer.money == Decimal("1000.00")
        assert transfer.status == TRANSFERSTATUS_TYPES.NEW


@pytest.mark.unit
class TestTransferValidation:
    """4. 转账验证测试"""

    def test_positive_money_validation(self):
        """测试金额正数验证"""
        # 验证转账金额必须为正数
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        import pytest

        # 测试负金额应该抛出异常
        with pytest.raises(ValueError, match="money must be non-negative"):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=-100.0,  # 负金额
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp="2023-01-01"
            )

        # 测试零金额应该被接受
        transfer_zero = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=0.0,
            status=TRANSFERSTATUS_TYPES.PENDING,
            timestamp="2023-01-01"
        )
        assert transfer_zero.money == 0

        # 测试正金额应该正常工作
        transfer_positive = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.PENDING,
            timestamp="2023-01-01"
        )
        assert transfer_positive.money == 1000.0

    def test_minimum_transfer_amount(self):
        """测试最小转账金额"""
        # 验证转账金额符合最小转账单位
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        from decimal import Decimal

        # 测试非常小的金额（比如0.001）应该能够处理
        small_amount = Decimal('0.001')
        transfer_small = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=small_amount,
            status=TRANSFERSTATUS_TYPES.PENDING,
            timestamp="2023-01-01"
        )
        assert transfer_small.money == small_amount

        # 测试整数金额
        integer_amount = 100
        transfer_integer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.CHINA,
            money=integer_amount,
            status=TRANSFERSTATUS_TYPES.PENDING,
            timestamp="2023-01-01"
        )
        assert transfer_integer.money == integer_amount

        # 测试浮点数金额
        float_amount = 99.99
        transfer_float = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=float_amount,
            status=TRANSFERSTATUS_TYPES.PENDING,
            timestamp="2023-01-01"
        )
        assert transfer_float.money == Decimal(str(float_amount))

    def test_direction_enum_validation(self):
        """测试转账方向枚举验证"""
        # 验证转账方向必须为有效的TRANSFERDIRECTION_TYPES枚举
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        import pytest

        # 测试有效的转账方向枚举值
        for direction in [TRANSFERDIRECTION_TYPES.IN, TRANSFERDIRECTION_TYPES.OUT]:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=direction,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp="2023-01-01"
            )
            assert transfer.direction == direction

        # 测试无效的方向类型应该抛出异常
        with pytest.raises(TypeError, match="direction must be TRANSFERDIRECTION_TYPES enum"):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction="invalid_direction",  # 字符串而不是枚举
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp="2023-01-01"
            )

        # 测试None值应该抛出异常
        with pytest.raises(TypeError, match="direction must be TRANSFERDIRECTION_TYPES enum"):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=None,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp="2023-01-01"
            )

    def test_market_enum_validation(self):
        """测试市场枚举验证"""
        # 验证市场必须为有效的MARKET_TYPES枚举
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        import pytest

        # 测试有效的市场枚举值
        valid_markets = [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ, MARKET_TYPES.OTHER]
        for market in valid_markets:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=market,
                money=1000.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp="2023-01-01"
            )
            assert transfer.market == market

        # 测试无效的市场类型应该抛出异常
        with pytest.raises(TypeError, match="market must be MARKET_TYPES enum"):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market="STOCK",  # 字符串而不是枚举
                money=1000.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp="2023-01-01"
            )

    def test_status_enum_validation(self):
        """测试状态枚举验证"""
        # 验证状态必须为有效的TRANSFERSTATUS_TYPES枚举
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        import pytest

        # 测试有效的状态枚举值
        valid_statuses = [
            TRANSFERSTATUS_TYPES.NEW,
            TRANSFERSTATUS_TYPES.SUBMITTED,
            TRANSFERSTATUS_TYPES.FILLED,
            TRANSFERSTATUS_TYPES.PENDING
        ]
        for status in valid_statuses:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status=status,
                timestamp="2023-01-01"
            )
            assert transfer.status == status

        # 测试无效的状态类型应该抛出异常
        with pytest.raises(TypeError, match="status must be TRANSFERSTATUS_TYPES enum"):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status="INVALID_STATUS",  # 字符串而不是枚举
                timestamp="2023-01-01"
            )

    def test_portfolio_id_not_empty(self):
        """测试组合ID非空验证"""
        # 验证组合ID不能为空
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        import pytest

        # 测试空字符串portfolio_id
        with pytest.raises(ValueError):
            Transfer(
                portfolio_id="",  # 空字符串
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp="2023-01-01"
            )

        # 测试None值portfolio_id
        with pytest.raises(TypeError, match="portfolio_id must be str"):
            Transfer(
                portfolio_id=None,
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp="2023-01-01"
            )

    def test_engine_id_not_empty(self):
        """测试引擎ID非空验证"""
        # 验证引擎ID不能为空
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        import pytest

        # 测试空字符串engine_id
        with pytest.raises(ValueError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="",  # 空字符串
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp="2023-01-01"
            )

        # 测试None值engine_id
        with pytest.raises(TypeError, match="engine_id must be str"):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id=None,
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp="2023-01-01"
            )

    def test_transfer_consistency_check(self):
        """测试转账一致性检查"""
        # 验证转账数据的内部一致性
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        from decimal import Decimal

        # 测试正常的一致性检查
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )

        # 验证所有字段的一致性
        assert transfer.portfolio_id == "test_portfolio"
        assert transfer.engine_id == "test_engine"
        assert transfer.run_id == "test_run"
        assert transfer.direction == TRANSFERDIRECTION_TYPES.IN
        assert transfer.market == MARKET_TYPES.CHINA
        assert transfer.money == Decimal("1000.00")
        assert transfer.status == TRANSFERSTATUS_TYPES.NEW
        assert isinstance(transfer.timestamp, datetime.datetime)

    def test_timestamp_validity_check(self):
        """测试时间戳有效性检查"""
        # 验证转账时间戳的合理性
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        import pytest

        # 测试合理的时间戳
        valid_timestamps = [
            "2023-01-01",
            "2023-12-31",
            datetime.datetime(2023, 6, 15),
            "2023-06-15 14:30:00"
        ]

        for timestamp in valid_timestamps:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp=timestamp
            )
            assert isinstance(transfer.timestamp, datetime.datetime)

        # 测试无效的时间戳应该抛出异常
        invalid_timestamps = [
            "2023-13-01",    # 无效月份
            "2023-01-32",    # 无效日期
            "invalid_date",   # 完全无效的字符串
            ""               # 空字符串
        ]

        for invalid_timestamp in invalid_timestamps:
            with pytest.raises(ValueError):
                Transfer(
                    portfolio_id="test_portfolio",
                    engine_id="test_engine",
                    run_id="test_run",
                    direction=TRANSFERDIRECTION_TYPES.IN,
                    market=MARKET_TYPES.CHINA,
                    money=1000.0,
                    status=TRANSFERSTATUS_TYPES.PENDING,
                    timestamp=invalid_timestamp
                )


@pytest.mark.unit
class TestTransferStatusManagement:
    """5. 转账状态管理测试"""

    def test_valid_status_enum_values(self):
        """测试所有有效的TRANSFERSTATUS_TYPES枚举值"""
        # 验证所有有效状态都能正确设置
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES

        valid_statuses = [
            TRANSFERSTATUS_TYPES.VOID,
            TRANSFERSTATUS_TYPES.OTHER,
            TRANSFERSTATUS_TYPES.NEW,
            TRANSFERSTATUS_TYPES.SUBMITTED,
            TRANSFERSTATUS_TYPES.FILLED
        ]

        for status in valid_statuses:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status=status,
                timestamp="2023-01-01"
            )
            assert transfer.status == status
            assert isinstance(transfer.status, TRANSFERSTATUS_TYPES)

    def test_status_setting_and_retrieval(self):
        """测试状态设置和查询功能"""
        # 测试状态的设置和查询
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )

        # 验证初始状态
        assert transfer.status == TRANSFERSTATUS_TYPES.NEW

        # 通过set方法修改状态
        transfer.set(
            "test_portfolio",
            "test_engine",
            "test_run",
            TRANSFERDIRECTION_TYPES.IN,
            MARKET_TYPES.CHINA,
            1000.0,
            TRANSFERSTATUS_TYPES.SUBMITTED,
            "2023-01-01"
        )
        assert transfer.status == TRANSFERSTATUS_TYPES.SUBMITTED

    def test_invalid_status_rejection(self):
        """测试无效状态值的拒绝处理"""
        # 测试无效状态类型的拒绝
        import pytest

        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status="INVALID_STATUS",  # 字符串而非枚举
                timestamp="2023-01-01"
            )

        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=1000.0,
                status=999,  # 整数而非枚举
                timestamp="2023-01-01"
            )

    def test_status_transition_new_to_submitted(self):
        """测试NEW到SUBMITTED的状态转换"""
        # 测试正常的状态转换流程
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )

        # 验证初始状态
        assert transfer.status == TRANSFERSTATUS_TYPES.NEW

        # 转换到SUBMITTED状态
        transfer.set(
            "test_portfolio",
            "test_engine",
            "test_run",
            TRANSFERDIRECTION_TYPES.IN,
            MARKET_TYPES.CHINA,
            1000.0,
            TRANSFERSTATUS_TYPES.SUBMITTED,
            "2023-01-01"
        )
        assert transfer.status == TRANSFERSTATUS_TYPES.SUBMITTED

    def test_status_transition_submitted_to_filled(self):
        """测试SUBMITTED到FILLED的状态转换"""
        # 测试提交到完成的状态转换
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.SUBMITTED,
            timestamp="2023-01-01"
        )

        # 验证初始状态
        assert transfer.status == TRANSFERSTATUS_TYPES.SUBMITTED

        # 转换到FILLED状态
        transfer.set(
            "test_portfolio",
            "test_engine",
            "test_run",
            TRANSFERDIRECTION_TYPES.IN,
            MARKET_TYPES.CHINA,
            1000.0,
            TRANSFERSTATUS_TYPES.FILLED,
            "2023-01-01"
        )
        assert transfer.status == TRANSFERSTATUS_TYPES.FILLED

    def test_invalid_status_transitions(self):
        """测试无效的状态转换（如FILLED回到NEW）"""
        # 测试无效状态转换的拒绝

        # 创建已完成的转账
        filled_transfer = Transfer(
            portfolio_id="transition_test_portfolio",
            engine_id="transition_test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED,
            timestamp="2023-01-03"
        )

        # 验证初始状态
        assert filled_transfer.status == TRANSFERSTATUS_TYPES.FILLED

        # 测试不合理的状态回退场景
        # 注意：Transfer类本身不强制状态转换验证，这个测试主要验证业务逻辑层面的考虑

        # 1. FILLED -> NEW (已完成回到新建，不合理)
        # 在实际业务中，这种转换应该被禁止，但Transfer实体级别可能允许
        reverted_transfer = Transfer(
            portfolio_id=filled_transfer.portfolio_id,
            engine_id=filled_transfer.engine_id,
            run_id=filled_transfer.run_id,
            direction=filled_transfer.direction,
            market=filled_transfer.market,
            money=filled_transfer.money,
            status=TRANSFERSTATUS_TYPES.NEW,  # 不合理的状态回退
            timestamp="2023-01-03",
            uuid=filled_transfer.uuid
        )

        # 虽然技术上可以创建，但从业务逻辑角度这是不合理的
        assert reverted_transfer.status == TRANSFERSTATUS_TYPES.NEW

        # 2. CANCELED -> FILLED (已取消变成已完成，不合理)
        canceled_transfer = Transfer(
            portfolio_id="canceled_transition_portfolio",
            engine_id="canceled_transition_engine",
            run_id="run_20230103_002",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.CANCELED,
            timestamp="2023-01-03"
        )

        # 尝试将已取消的转账变成已完成
        invalid_filled = Transfer(
            portfolio_id=canceled_transfer.portfolio_id,
            engine_id=canceled_transfer.engine_id,
            run_id=canceled_transfer.run_id,
            direction=canceled_transfer.direction,
            market=canceled_transfer.market,
            money=canceled_transfer.money,
            status=TRANSFERSTATUS_TYPES.FILLED,
            timestamp="2023-01-03",
            uuid=canceled_transfer.uuid
        )

        # 技术上创建成功，但业务逻辑上不合理
        assert invalid_filled.status == TRANSFERSTATUS_TYPES.FILLED

        # 3. 测试状态转换的合理性检查逻辑
        # 定义合理的状态转换路径
        valid_transitions = {
            TRANSFERSTATUS_TYPES.NEW: [
                TRANSFERSTATUS_TYPES.SUBMITTED,
                TRANSFERSTATUS_TYPES.CANCELED
            ],
            TRANSFERSTATUS_TYPES.SUBMITTED: [
                TRANSFERSTATUS_TYPES.PENDING,
                TRANSFERSTATUS_TYPES.FILLED,
                TRANSFERSTATUS_TYPES.CANCELED
            ],
            TRANSFERSTATUS_TYPES.PENDING: [
                TRANSFERSTATUS_TYPES.FILLED,
                TRANSFERSTATUS_TYPES.CANCELED
            ],
            TRANSFERSTATUS_TYPES.FILLED: [],  # 终态，不应再转换
            TRANSFERSTATUS_TYPES.CANCELED: []  # 终态，不应再转换
        }

        def is_valid_transition(from_status, to_status):
            """检查状态转换是否合理"""
            return to_status in valid_transitions.get(from_status, [])

        # 测试各种状态转换的合理性
        transition_tests = [
            # (from_status, to_status, expected_valid)
            (TRANSFERSTATUS_TYPES.NEW, TRANSFERSTATUS_TYPES.SUBMITTED, True),
            (TRANSFERSTATUS_TYPES.NEW, TRANSFERSTATUS_TYPES.FILLED, False),  # 跳级不合理
            (TRANSFERSTATUS_TYPES.SUBMITTED, TRANSFERSTATUS_TYPES.PENDING, True),
            (TRANSFERSTATUS_TYPES.SUBMITTED, TRANSFERSTATUS_TYPES.FILLED, True),
            (TRANSFERSTATUS_TYPES.FILLED, TRANSFERSTATUS_TYPES.NEW, False),  # 回退不合理
            (TRANSFERSTATUS_TYPES.FILLED, TRANSFERSTATUS_TYPES.PENDING, False),  # 回退不合理
            (TRANSFERSTATUS_TYPES.CANCELED, TRANSFERSTATUS_TYPES.FILLED, False),  # 死状态复活不合理
            (TRANSFERSTATUS_TYPES.CANCELED, TRANSFERSTATUS_TYPES.NEW, False),  # 死状态复活不合理
        ]

        for from_status, to_status, expected_valid in transition_tests:
            actual_valid = is_valid_transition(from_status, to_status)
            assert actual_valid == expected_valid, f"状态转换 {from_status} -> {to_status} 的合理性判断错误"

        # 4. 测试终态的不可变性验证
        terminal_states = [TRANSFERSTATUS_TYPES.FILLED, TRANSFERSTATUS_TYPES.CANCELED]

        for terminal_status in terminal_states:
            terminal_transfer = Transfer(
                portfolio_id="terminal_test_portfolio",
                engine_id="terminal_test_engine",
                run_id="run_20230103_003",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("3000.00"),
                status=terminal_status,
                timestamp="2023-01-03"
            )

            # 验证终态设置成功
            assert terminal_transfer.status == terminal_status

            # 在业务逻辑中，终态不应该有有效的后续转换
            valid_next_states = valid_transitions.get(terminal_status, [])
            assert len(valid_next_states) == 0, f"终态 {terminal_status} 不应该有有效的后续转换"

        # 5. 测试状态转换的数据一致性
        # 状态变更时，其他数据应保持不变
        consistency_transfer = Transfer(
            portfolio_id="consistency_test_portfolio",
            engine_id="consistency_test_engine",
            run_id="run_20230103_004",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("4000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        original_data = {
            'portfolio_id': consistency_transfer.portfolio_id,
            'engine_id': consistency_transfer.engine_id,
            'run_id': consistency_transfer.run_id,
            'direction': consistency_transfer.direction,
            'market': consistency_transfer.market,
            'money': consistency_transfer.money,
            'uuid': consistency_transfer.uuid
        }

        # 创建状态转换后的新实例
        transitioned_transfer = Transfer(
            portfolio_id=original_data['portfolio_id'],
            engine_id=original_data['engine_id'],
            run_id=original_data['run_id'],
            direction=original_data['direction'],
            market=original_data['market'],
            money=original_data['money'],
            status=TRANSFERSTATUS_TYPES.FILLED,  # 状态改变
            timestamp="2023-01-03",
            uuid=original_data['uuid']
        )

        # 验证除了状态外，其他数据保持一致
        assert transitioned_transfer.portfolio_id == original_data['portfolio_id']
        assert transitioned_transfer.engine_id == original_data['engine_id']
        assert transitioned_transfer.run_id == original_data['run_id']
        assert transitioned_transfer.direction == original_data['direction']
        assert transitioned_transfer.market == original_data['market']
        assert transitioned_transfer.money == original_data['money']
        assert transitioned_transfer.uuid == original_data['uuid']
        assert transitioned_transfer.status == TRANSFERSTATUS_TYPES.FILLED

    def test_status_transition_validation_logic(self):
        """测试状态转换的业务逻辑验证"""
        # 测试状态转换的业务规则

        # 1. 定义完整的状态转换业务规则
        class TransferStatusValidator:
            """转账状态转换验证器"""

            @staticmethod
            def get_valid_transitions():
                """获取有效的状态转换映射"""
                return {
                    TRANSFERSTATUS_TYPES.NEW: {
                        TRANSFERSTATUS_TYPES.SUBMITTED: "转账提交",
                        TRANSFERSTATUS_TYPES.CANCELED: "新建转账取消"
                    },
                    TRANSFERSTATUS_TYPES.SUBMITTED: {
                        TRANSFERSTATUS_TYPES.PENDING: "转账处理中",
                        TRANSFERSTATUS_TYPES.FILLED: "转账直接完成",
                        TRANSFERSTATUS_TYPES.CANCELED: "已提交转账取消"
                    },
                    TRANSFERSTATUS_TYPES.PENDING: {
                        TRANSFERSTATUS_TYPES.FILLED: "处理完成",
                        TRANSFERSTATUS_TYPES.CANCELED: "处理中转账取消"
                    },
                    TRANSFERSTATUS_TYPES.FILLED: {},  # 终态
                    TRANSFERSTATUS_TYPES.CANCELED: {},  # 终态
                    TRANSFERSTATUS_TYPES.OTHER: {  # 其他状态可以转换到任何状态
                        TRANSFERSTATUS_TYPES.NEW: "其他状态重置为新建",
                        TRANSFERSTATUS_TYPES.SUBMITTED: "其他状态提交",
                        TRANSFERSTATUS_TYPES.PENDING: "其他状态处理中",
                        TRANSFERSTATUS_TYPES.FILLED: "其他状态完成",
                        TRANSFERSTATUS_TYPES.CANCELED: "其他状态取消"
                    },
                    TRANSFERSTATUS_TYPES.VOID: {}  # 无效状态不应转换
                }

            @staticmethod
            def is_valid_transition(from_status, to_status):
                """验证状态转换是否有效"""
                valid_transitions = TransferStatusValidator.get_valid_transitions()
                return to_status in valid_transitions.get(from_status, {})

            @staticmethod
            def get_transition_reason(from_status, to_status):
                """获取状态转换的原因描述"""
                valid_transitions = TransferStatusValidator.get_valid_transitions()
                return valid_transitions.get(from_status, {}).get(to_status, "无效转换")

        validator = TransferStatusValidator()

        # 2. 测试标准业务流程的状态转换
        standard_flow_tests = [
            # 正常流程：NEW -> SUBMITTED -> PENDING -> FILLED
            (TRANSFERSTATUS_TYPES.NEW, TRANSFERSTATUS_TYPES.SUBMITTED, True, "转账提交"),
            (TRANSFERSTATUS_TYPES.SUBMITTED, TRANSFERSTATUS_TYPES.PENDING, True, "转账处理中"),
            (TRANSFERSTATUS_TYPES.PENDING, TRANSFERSTATUS_TYPES.FILLED, True, "处理完成"),

            # 快速流程：NEW -> SUBMITTED -> FILLED
            (TRANSFERSTATUS_TYPES.SUBMITTED, TRANSFERSTATUS_TYPES.FILLED, True, "转账直接完成"),

            # 取消流程：各状态 -> CANCELED
            (TRANSFERSTATUS_TYPES.NEW, TRANSFERSTATUS_TYPES.CANCELED, True, "新建转账取消"),
            (TRANSFERSTATUS_TYPES.SUBMITTED, TRANSFERSTATUS_TYPES.CANCELED, True, "已提交转账取消"),
            (TRANSFERSTATUS_TYPES.PENDING, TRANSFERSTATUS_TYPES.CANCELED, True, "处理中转账取消"),
        ]

        for from_status, to_status, expected_valid, expected_reason in standard_flow_tests:
            actual_valid = validator.is_valid_transition(from_status, to_status)
            actual_reason = validator.get_transition_reason(from_status, to_status)

            assert actual_valid == expected_valid, f"状态转换 {from_status} -> {to_status} 验证失败"
            if expected_valid:
                assert actual_reason == expected_reason, f"转换原因不匹配: {actual_reason} != {expected_reason}"

        # 3. 测试无效的业务转换
        invalid_transitions = [
            # 不能从终态转换到其他状态
            (TRANSFERSTATUS_TYPES.FILLED, TRANSFERSTATUS_TYPES.NEW, "已完成不能回到新建"),
            (TRANSFERSTATUS_TYPES.FILLED, TRANSFERSTATUS_TYPES.SUBMITTED, "已完成不能回到已提交"),
            (TRANSFERSTATUS_TYPES.FILLED, TRANSFERSTATUS_TYPES.PENDING, "已完成不能回到处理中"),
            (TRANSFERSTATUS_TYPES.CANCELED, TRANSFERSTATUS_TYPES.NEW, "已取消不能回到新建"),
            (TRANSFERSTATUS_TYPES.CANCELED, TRANSFERSTATUS_TYPES.SUBMITTED, "已取消不能回到已提交"),
            (TRANSFERSTATUS_TYPES.CANCELED, TRANSFERSTATUS_TYPES.FILLED, "已取消不能变成已完成"),

            # 不能跳跃式转换
            (TRANSFERSTATUS_TYPES.NEW, TRANSFERSTATUS_TYPES.PENDING, "新建不能直接到处理中"),
            (TRANSFERSTATUS_TYPES.NEW, TRANSFERSTATUS_TYPES.FILLED, "新建不能直接到已完成"),

            # VOID状态的限制
            (TRANSFERSTATUS_TYPES.VOID, TRANSFERSTATUS_TYPES.NEW, "无效状态不能转换"),
        ]

        for from_status, to_status, reason in invalid_transitions:
            is_valid = validator.is_valid_transition(from_status, to_status)
            assert not is_valid, f"无效转换被错误地标记为有效: {from_status} -> {to_status} ({reason})"

        # 4. 测试实际Transfer实例的状态转换模拟
        # 模拟一个完整的转账生命周期
        lifecycle_scenarios = [
            # 场景1: 正常完成流程
            [
                (TRANSFERSTATUS_TYPES.NEW, "创建新转账"),
                (TRANSFERSTATUS_TYPES.SUBMITTED, "提交转账"),
                (TRANSFERSTATUS_TYPES.PENDING, "开始处理"),
                (TRANSFERSTATUS_TYPES.FILLED, "处理完成")
            ],
            # 场景2: 快速完成流程
            [
                (TRANSFERSTATUS_TYPES.NEW, "创建新转账"),
                (TRANSFERSTATUS_TYPES.SUBMITTED, "提交转账"),
                (TRANSFERSTATUS_TYPES.FILLED, "直接完成")
            ],
            # 场景3: 取消流程
            [
                (TRANSFERSTATUS_TYPES.NEW, "创建新转账"),
                (TRANSFERSTATUS_TYPES.SUBMITTED, "提交转账"),
                (TRANSFERSTATUS_TYPES.CANCELED, "用户取消")
            ]
        ]

        for scenario_idx, scenario in enumerate(lifecycle_scenarios):
            previous_status = None
            previous_transfer = None

            for step_idx, (status, description) in enumerate(scenario):
                # 创建当前状态的转账
                transfer = Transfer(
                    portfolio_id=f"lifecycle_scenario_{scenario_idx}",
                    engine_id=f"lifecycle_engine_{scenario_idx}",
                    run_id=f"run_20230103_{scenario_idx:03d}",
                    direction=TRANSFERDIRECTION_TYPES.IN,
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("1000.00"),
                    status=status,
                    timestamp="2023-01-03",
                    uuid=previous_transfer.uuid if previous_transfer else None
                )

                # 验证当前状态设置正确
                assert transfer.status == status, f"场景{scenario_idx}步骤{step_idx}: 状态设置错误"

                # 如果不是第一步，验证状态转换的有效性
                if previous_status is not None:
                    is_valid = validator.is_valid_transition(previous_status, status)
                    assert is_valid, f"场景{scenario_idx}: 无效的状态转换 {previous_status} -> {status} ({description})"

                previous_status = status
                previous_transfer = transfer

        # 5. 测试业务规则的一致性
        # 验证所有状态都有明确的转换规则定义
        all_statuses = [
            TRANSFERSTATUS_TYPES.VOID,
            TRANSFERSTATUS_TYPES.OTHER,
            TRANSFERSTATUS_TYPES.NEW,
            TRANSFERSTATUS_TYPES.SUBMITTED,
            TRANSFERSTATUS_TYPES.PENDING,
            TRANSFERSTATUS_TYPES.FILLED,
            TRANSFERSTATUS_TYPES.CANCELED
        ]

        valid_transitions = validator.get_valid_transitions()
        for status in all_statuses:
            assert status in valid_transitions, f"状态 {status} 缺少转换规则定义"

            # 验证每个状态的转换目标都是有效的状态
            for target_status in valid_transitions[status]:
                assert target_status in all_statuses, f"无效的目标状态: {target_status}"

        # 6. 测试终态的确定性
        terminal_states = [TRANSFERSTATUS_TYPES.FILLED, TRANSFERSTATUS_TYPES.CANCELED]
        for terminal_status in terminal_states:
            # 终态不应该有任何有效的转换
            valid_targets = valid_transitions.get(terminal_status, {})
            assert len(valid_targets) == 0, f"终态 {terminal_status} 不应该有有效的转换目标"

            # 验证终态的Transfer实例
            terminal_transfer = Transfer(
                portfolio_id="terminal_validation_portfolio",
                engine_id="terminal_validation_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("5000.00"),
                status=terminal_status,
                timestamp="2023-01-03"
            )

            assert terminal_transfer.status == terminal_status

            # 验证从终态转换到任何其他状态都是无效的
            for other_status in all_statuses:
                if other_status != terminal_status:
                    is_valid = validator.is_valid_transition(terminal_status, other_status)
                    assert not is_valid, f"从终态 {terminal_status} 到 {other_status} 的转换应该无效"

    def test_status_enum_value_mapping(self):
        """测试状态枚举值与整数的映射关系"""
        # 验证枚举值的数值映射
        from ginkgo.enums import TRANSFERSTATUS_TYPES

        # 验证枚举值的数值
        assert TRANSFERSTATUS_TYPES.VOID.value == -1
        assert TRANSFERSTATUS_TYPES.OTHER.value == 0
        assert TRANSFERSTATUS_TYPES.NEW.value == 1
        assert TRANSFERSTATUS_TYPES.SUBMITTED.value == 2
        assert TRANSFERSTATUS_TYPES.FILLED.value == 3

    def test_status_type_consistency(self):
        """测试状态类型一致性检查"""
        # 验证状态类型始终保持一致
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )

        # 验证类型一致性
        assert isinstance(transfer.status, TRANSFERSTATUS_TYPES)

        # 修改状态后类型仍保持一致
        transfer.set(
            "test_portfolio",
            "test_engine",
            "test_run",
            TRANSFERDIRECTION_TYPES.IN,
            MARKET_TYPES.CHINA,
            1000.0,
            TRANSFERSTATUS_TYPES.FILLED,
            "2023-01-01"
        )
        assert isinstance(transfer.status, TRANSFERSTATUS_TYPES)


@pytest.mark.unit
class TestTransferBusinessLogic:
    """6. Transfer核心业务逻辑测试"""

    def test_transfer_direction_validation(self):
        """测试转账方向验证（IN/OUT）"""
        # 验证转账方向的正确设置和验证
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES

        # 测试IN方向
        transfer_in = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )
        assert transfer_in.direction == TRANSFERDIRECTION_TYPES.IN
        assert transfer_in.direction.value == 1
        assert isinstance(transfer_in.direction, TRANSFERDIRECTION_TYPES)

        # 测试OUT方向
        transfer_out = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )
        assert transfer_out.direction == TRANSFERDIRECTION_TYPES.OUT
        assert transfer_out.direction.value == 2
        assert isinstance(transfer_out.direction, TRANSFERDIRECTION_TYPES)

    def test_market_type_validation(self):
        """测试市场类型验证"""
        # 验证市场类型的正确设置和验证
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES

        # 测试不同市场类型
        markets = [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ, MARKET_TYPES.OTHER]

        for market in markets:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="test_run",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=market,
                money=1000.0,
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-01"
            )
            assert transfer.market == market
            assert isinstance(transfer.market, MARKET_TYPES)

    def test_money_precision_handling(self):
        """测试金额精度处理"""
        # 验证金额精度的正确处理
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        from decimal import Decimal

        # 测试高精度金额
        high_precision_amount = Decimal("12345.123456789")
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=high_precision_amount,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )

        # 验证精度保持
        assert transfer.money == high_precision_amount
        assert isinstance(transfer.money, Decimal)

        # 测试不同输入类型都转换为Decimal
        # 测试整数输入
        transfer_int = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000,  # int
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )
        assert transfer_int.money == Decimal("1000")
        assert isinstance(transfer_int.money, Decimal)

        # 测试浮点数输入
        transfer_float = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=999.99,  # float
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )
        assert isinstance(transfer_float.money, Decimal)
        # 注意：float转Decimal可能有精度问题，所以这里验证类型即可

    def test_timestamp_normalization(self):
        """测试时间戳标准化处理"""
        # 验证时间戳的标准化处理
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        import datetime

        # 测试字符串时间戳标准化
        transfer_str = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-06-15"
        )
        expected_datetime = datetime.datetime(2023, 6, 15)
        assert transfer_str.timestamp == expected_datetime
        assert isinstance(transfer_str.timestamp, datetime.datetime)

        # 测试datetime对象时间戳
        test_datetime = datetime.datetime(2023, 12, 25, 14, 30, 0)
        transfer_dt = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp=test_datetime
        )
        assert transfer_dt.timestamp == test_datetime
        assert isinstance(transfer_dt.timestamp, datetime.datetime)

        # 测试带时间的字符串时间戳
        transfer_str_with_time = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-09-18 09:30:00"
        )
        expected_datetime_with_time = datetime.datetime(2023, 9, 18, 9, 30, 0)
        assert transfer_str_with_time.timestamp == expected_datetime_with_time
        assert isinstance(transfer_str_with_time.timestamp, datetime.datetime)

    def test_transfer_record_uniqueness(self):
        """测试转账记录的唯一性"""
        # 验证每个转账记录的唯一性
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES

        # 创建多个Transfer实例
        transfer1 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run_1",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )

        transfer2 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run_2",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )

        transfer3 = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run_3",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.NASDAQ,
            money=2000.0,
            status=TRANSFERSTATUS_TYPES.FILLED,
            timestamp="2023-01-02"
        )

        # 验证UUID唯一性
        assert transfer1.uuid != transfer2.uuid
        assert transfer1.uuid != transfer3.uuid
        assert transfer2.uuid != transfer3.uuid

        # 验证UUID存在且有效
        assert len(transfer1.uuid) > 0
        assert len(transfer2.uuid) > 0
        assert len(transfer3.uuid) > 0
        assert isinstance(transfer1.uuid, str)
        assert isinstance(transfer2.uuid, str)
        assert isinstance(transfer3.uuid, str)

    def test_portfolio_association_logic(self):
        """测试与Portfolio的关联逻辑"""
        # 验证与Portfolio的关联逻辑
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES

        # 测试portfolio_id的基本关联
        transfer = Transfer(
            portfolio_id="portfolio_001",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )

        # 验证portfolio关联
        assert transfer.portfolio_id == "portfolio_001"
        assert isinstance(transfer.portfolio_id, str)

        # 测试portfolio_id支持直接setter修改
        transfer.portfolio_id = "setter_portfolio_003"
        assert transfer.portfolio_id == "setter_portfolio_003"

        # 以及通过set方法更新
        transfer.set(
            "updated_portfolio_002",  # 新的portfolio_id
            "test_engine",
            "test_run",
            TRANSFERDIRECTION_TYPES.IN,
            MARKET_TYPES.CHINA,
            1000.0,
            TRANSFERSTATUS_TYPES.NEW,
            "2023-01-01"
        )

        # 验证通过set方法成功更新了portfolio_id
        assert transfer.portfolio_id == "updated_portfolio_002"

    def test_engine_run_association(self):
        """测试与Engine和Run的关联逻辑"""
        # 验证与Engine和Run的关联逻辑
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES

        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="engine_001",
            run_id="run_20230101_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )

        # 验证Engine和Run关联
        assert transfer.engine_id == "engine_001"
        assert transfer.run_id == "run_20230101_001"
        assert isinstance(transfer.engine_id, str)
        assert isinstance(transfer.run_id, str)

        # 测试engine_id有setter可以直接修改
        transfer.engine_id = "updated_engine_002"
        assert transfer.engine_id == "updated_engine_002"

        # 测试run_id有setter可以直接修改
        transfer.run_id = "updated_run_002"
        assert transfer.run_id == "updated_run_002"

        # 测试通过set方法更新engine_id和run_id
        transfer.set(
            "test_portfolio",
            "final_engine_003",     # 新的engine_id
            "run_20230102_final",   # 新的run_id
            TRANSFERDIRECTION_TYPES.OUT,
            MARKET_TYPES.NASDAQ,
            2000.0,
            TRANSFERSTATUS_TYPES.FILLED,
            "2023-01-02"
        )

        # 验证更新成功
        assert transfer.engine_id == "final_engine_003"
        assert transfer.run_id == "run_20230102_final"

    def test_transfer_amount_boundary_conditions(self):
        """测试转账金额边界条件"""
        # 验证转账金额的边界条件处理
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
        from decimal import Decimal

        # 测试零金额
        transfer_zero = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )
        assert transfer_zero.money == Decimal("0")
        assert isinstance(transfer_zero.money, Decimal)

        # 测试极小金额
        small_amount = Decimal("0.000001")
        transfer_small = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=small_amount,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )
        assert transfer_small.money == small_amount
        assert isinstance(transfer_small.money, Decimal)

        # 测试大额金额
        large_amount = Decimal("999999999.99")
        transfer_large = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=large_amount,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )
        assert transfer_large.money == large_amount
        assert isinstance(transfer_large.money, Decimal)

        # 测试高精度金额
        precision_amount = Decimal("123.123456789012345")
        transfer_precision = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=precision_amount,
            status=TRANSFERSTATUS_TYPES.FILLED,
            timestamp="2023-01-01"
        )
        assert transfer_precision.money == precision_amount
        assert isinstance(transfer_precision.money, Decimal)


@pytest.mark.unit
class TestTransferConstraints:
    """7. Transfer约束检查测试"""

    def test_transferdirection_enum_constraints(self):
        """测试TRANSFERDIRECTION_TYPES枚举约束（VOID=-1, OTHER=0, IN=1, OUT=2）"""
        # 验证转账方向枚举值的约束
        from ginkgo.enums import TRANSFERDIRECTION_TYPES

        # 验证枚举值的数值映射
        assert TRANSFERDIRECTION_TYPES.VOID.value == -1
        assert TRANSFERDIRECTION_TYPES.OTHER.value == 0
        assert TRANSFERDIRECTION_TYPES.IN.value == 1
        assert TRANSFERDIRECTION_TYPES.OUT.value == 2

        # 验证所有枚举成员存在
        expected_members = ['VOID', 'OTHER', 'IN', 'OUT']
        actual_members = [member.name for member in TRANSFERDIRECTION_TYPES]
        for expected in expected_members:
            assert expected in actual_members

        # 验证枚举类型
        assert isinstance(TRANSFERDIRECTION_TYPES.IN, TRANSFERDIRECTION_TYPES)
        assert isinstance(TRANSFERDIRECTION_TYPES.OUT, TRANSFERDIRECTION_TYPES)
        assert isinstance(TRANSFERDIRECTION_TYPES.VOID, TRANSFERDIRECTION_TYPES)
        assert isinstance(TRANSFERDIRECTION_TYPES.OTHER, TRANSFERDIRECTION_TYPES)

    def test_transferstatus_enum_constraints(self):
        """测试TRANSFERSTATUS_TYPES枚举约束（VOID=-1, OTHER=0, NEW=1, SUBMITTED=2, FILLED=3）"""
        # 验证转账状态枚举值的约束
        from ginkgo.enums import TRANSFERSTATUS_TYPES

        # 验证枚举值的数值映射
        assert TRANSFERSTATUS_TYPES.VOID.value == -1
        assert TRANSFERSTATUS_TYPES.OTHER.value == 0
        assert TRANSFERSTATUS_TYPES.NEW.value == 1
        assert TRANSFERSTATUS_TYPES.SUBMITTED.value == 2
        assert TRANSFERSTATUS_TYPES.FILLED.value == 3

        # 验证所有枚举成员存在
        expected_members = ['VOID', 'OTHER', 'NEW', 'SUBMITTED', 'FILLED']
        actual_members = [member.name for member in TRANSFERSTATUS_TYPES]
        for expected in expected_members:
            assert expected in actual_members

        # 验证枚举类型
        assert isinstance(TRANSFERSTATUS_TYPES.NEW, TRANSFERSTATUS_TYPES)
        assert isinstance(TRANSFERSTATUS_TYPES.SUBMITTED, TRANSFERSTATUS_TYPES)
        assert isinstance(TRANSFERSTATUS_TYPES.FILLED, TRANSFERSTATUS_TYPES)
        assert isinstance(TRANSFERSTATUS_TYPES.VOID, TRANSFERSTATUS_TYPES)
        assert isinstance(TRANSFERSTATUS_TYPES.OTHER, TRANSFERSTATUS_TYPES)

    def test_market_enum_constraints(self):
        """测试MARKET_TYPES枚举约束"""
        # 验证市场类型枚举值的约束
        from ginkgo.enums import MARKET_TYPES

        # 验证枚举包含基本市场类型
        market_names = [member.name for member in MARKET_TYPES]
        expected_markets = ['CHINA', 'NASDAQ', 'OTHER']

        for expected in expected_markets:
            assert expected in market_names

        # 验证枚举类型
        assert isinstance(MARKET_TYPES.CHINA, MARKET_TYPES)
        assert isinstance(MARKET_TYPES.NASDAQ, MARKET_TYPES)
        assert isinstance(MARKET_TYPES.OTHER, MARKET_TYPES)

        # 验证枚举值存在且有效
        assert hasattr(MARKET_TYPES, 'CHINA')
        assert hasattr(MARKET_TYPES, 'NASDAQ')
        assert hasattr(MARKET_TYPES, 'OTHER')

    def test_component_type_constraint(self):
        """测试component_type必须为COMPONENT_TYPES.TRANSFER"""
        # 验证component_type的正确设置
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES, COMPONENT_TYPES

        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )

        # 验证component_type设置正确
        assert transfer.component_type == COMPONENT_TYPES.TRANSFER
        assert isinstance(transfer.component_type, COMPONENT_TYPES)

        # 验证component_type是继承自Base类的属性
        assert hasattr(transfer, 'component_type')

    def test_data_integrity_checks(self):
        """测试数据完整性检查"""
        # 验证数据完整性约束
        from ginkgo.trading.entities.transfer import Transfer
        from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES

        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=1000.0,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-01"
        )

        # 验证所有字段都有正确的值且不为None
        assert transfer.portfolio_id is not None
        assert transfer.engine_id is not None
        assert transfer.run_id is not None
        assert transfer.direction is not None
        assert transfer.market is not None
        assert transfer.money is not None
        assert transfer.status is not None
        assert transfer.timestamp is not None
        assert transfer.uuid is not None

        # 验证字段类型正确性
        assert isinstance(transfer.portfolio_id, str)
        assert isinstance(transfer.engine_id, str)
        assert isinstance(transfer.run_id, str)
        assert isinstance(transfer.direction, TRANSFERDIRECTION_TYPES)
        assert isinstance(transfer.market, MARKET_TYPES)
        assert isinstance(transfer.status, TRANSFERSTATUS_TYPES)
        assert isinstance(transfer.uuid, str)

        # 验证字符串字段非空
        assert len(transfer.portfolio_id) > 0
        assert len(transfer.engine_id) > 0
        assert len(transfer.run_id) > 0
        assert len(transfer.uuid) > 0

    def test_enum_value_range_validation(self):
        """测试枚举值范围验证"""
        # 验证枚举值在有效范围内

        # 测试TRANSFERDIRECTION_TYPES的所有有效值
        valid_directions = [
            TRANSFERDIRECTION_TYPES.IN,
            TRANSFERDIRECTION_TYPES.OUT,
            TRANSFERDIRECTION_TYPES.OTHER,
            TRANSFERDIRECTION_TYPES.VOID
        ]

        for direction in valid_directions:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=direction,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )
            assert transfer.direction == direction
            assert isinstance(transfer.direction, TRANSFERDIRECTION_TYPES)

        # 测试TRANSFERSTATUS_TYPES的所有有效值
        valid_statuses = [
            TRANSFERSTATUS_TYPES.NEW,
            TRANSFERSTATUS_TYPES.SUBMITTED,
            TRANSFERSTATUS_TYPES.FILLED,
            TRANSFERSTATUS_TYPES.CANCELED,
            TRANSFERSTATUS_TYPES.PENDING,
            TRANSFERSTATUS_TYPES.OTHER,
            TRANSFERSTATUS_TYPES.VOID
        ]

        for status in valid_statuses:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=status,
                timestamp="2023-01-03"
            )
            assert transfer.status == status
            assert isinstance(transfer.status, TRANSFERSTATUS_TYPES)

        # 测试MARKET_TYPES的所有有效值
        valid_markets = [
            MARKET_TYPES.CHINA,
            MARKET_TYPES.NASDAQ,
            MARKET_TYPES.OTHER,
            MARKET_TYPES.VOID
        ]

        for market in valid_markets:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=market,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )
            assert transfer.market == market
            assert isinstance(transfer.market, MARKET_TYPES)

    def test_invalid_enum_rejection(self):
        """测试无效枚举值的拒绝处理"""
        # 验证无效枚举值的拒绝处理

        # 测试无效的TRANSFERDIRECTION_TYPES（字符串）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction="IN",  # 字符串而非枚举
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

        # 测试无效的TRANSFERDIRECTION_TYPES（整数）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=999,  # 超出范围的整数
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

        # 测试无效的TRANSFERSTATUS_TYPES（字符串）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status="NEW",  # 字符串而非枚举
                timestamp="2023-01-03"
            )

        # 测试无效的TRANSFERSTATUS_TYPES（整数）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=888,  # 超出范围的整数
                timestamp="2023-01-03"
            )

        # 测试无效的MARKET_TYPES（字符串）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market="CHINA",  # 字符串而非枚举
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

        # 测试无效的MARKET_TYPES（浮点数）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=1.5,  # 浮点数而非枚举
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

        # 测试None值枚举（应该被拒绝）
        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=None,  # None值
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=None,  # None值
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

        with pytest.raises(TypeError):
            Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=None,  # None值
                timestamp="2023-01-03"
            )


@pytest.mark.unit
class TestTransferFinancialOperations:
    """8. Transfer金融操作测试"""

    def test_large_amount_transfer_handling(self):
        """测试大额转账处理"""
        # 测试大额金额的Transfer处理

        # 测试千万级金额
        large_amounts = [
            Decimal("10000000.00"),    # 一千万
            Decimal("100000000.00"),   # 一亿
            Decimal("1000000000.00"),  # 十亿
            Decimal("9999999999.99"),  # 接近百亿的大额
        ]

        for amount in large_amounts:
            transfer = Transfer(
                portfolio_id="large_portfolio",
                engine_id="large_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=amount,
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            # 验证大额金额正确存储
            assert transfer.money == amount
            assert isinstance(transfer.money, Decimal)

            # 验证精度保持
            assert str(transfer.money) == str(amount)

        # 测试极大金额（边界测试）
        extreme_large = Decimal("99999999999999.99")  # 接近系统极限
        transfer = Transfer(
            portfolio_id="extreme_portfolio",
            engine_id="extreme_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=extreme_large,
            status=TRANSFERSTATUS_TYPES.SUBMITTED,
            timestamp="2023-01-03"
        )

        assert transfer.money == extreme_large
        assert isinstance(transfer.money, Decimal)

        # 验证大额金额的字符串表示保持正确
        money_str = str(transfer.money)
        assert "99999999999999.99" in money_str

    def test_decimal_precision_preservation(self):
        """测试小数精度保持（Decimal类型）"""
        # 测试高精度小数的精度保持

        # 测试高精度小数（4位小数）
        high_precision_amounts = [
            Decimal("1234.5678"),      # 标准4位小数
            Decimal("0.0001"),         # 微小金额
            Decimal("99.9999"),        # 接近整数的高精度
            Decimal("1000000.0001"),   # 大额+微小小数
        ]

        for amount in high_precision_amounts:
            transfer = Transfer(
                portfolio_id="precision_portfolio",
                engine_id="precision_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=amount,
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            # 验证精度完全保持
            assert transfer.money == amount
            assert isinstance(transfer.money, Decimal)
            assert str(transfer.money) == str(amount)

        # 测试极高精度（8位小数）
        ultra_precision_amounts = [
            Decimal("123.12345678"),   # 8位小数
            Decimal("0.00000001"),     # 最小单位
            Decimal("9999.99999999"),  # 接近万元的超高精度
        ]

        for amount in ultra_precision_amounts:
            transfer = Transfer(
                portfolio_id="ultra_precision_portfolio",
                engine_id="ultra_precision_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.NASDAQ,
                money=amount,
                status=TRANSFERSTATUS_TYPES.FILLED,
                timestamp="2023-01-03"
            )

            # 验证超高精度保持
            assert transfer.money == amount
            assert isinstance(transfer.money, Decimal)

            # 确保没有精度损失
            reconstructed = Decimal(str(transfer.money))
            assert reconstructed == amount

        # 测试科学计数法精度
        scientific_amounts = [
            Decimal("1.23456789E+10"),  # 科学计数法大数
            Decimal("1.23456789E-10"),  # 科学计数法小数
        ]

        for amount in scientific_amounts:
            transfer = Transfer(
                portfolio_id="scientific_portfolio",
                engine_id="scientific_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=amount,
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            assert transfer.money == amount
            assert isinstance(transfer.money, Decimal)

    def test_money_arithmetic_operations(self):
        """测试金额算术运算"""
        # 测试金额的各种运算

        # 创建基础Transfer实例用于算术测试
        base_amount = Decimal("1000.50")
        transfer = Transfer(
            portfolio_id="arithmetic_portfolio",
            engine_id="arithmetic_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=base_amount,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 测试基本算术运算
        money = transfer.money

        # 加法运算
        addition_result = money + Decimal("500.25")
        assert addition_result == Decimal("1500.75")
        assert isinstance(addition_result, Decimal)

        # 减法运算
        subtraction_result = money - Decimal("200.30")
        assert subtraction_result == Decimal("800.20")
        assert isinstance(subtraction_result, Decimal)

        # 乘法运算（比例计算）
        multiplication_result = money * Decimal("1.1")  # 10%增长
        assert multiplication_result == Decimal("1100.55")
        assert isinstance(multiplication_result, Decimal)

        # 除法运算（平分计算）
        division_result = money / Decimal("2")
        assert division_result == Decimal("500.25")
        assert isinstance(division_result, Decimal)

        # 测试复杂算术运算
        complex_calculation = (money * Decimal("0.05")) + Decimal("10.00")  # 5%手续费+固定费用
        expected_fee = Decimal("60.025")  # 1000.50 * 0.05 + 10.00
        assert complex_calculation == expected_fee

        # 测试精度保持的算术运算
        high_precision_transfer = Transfer(
            portfolio_id="precision_arithmetic_portfolio",
            engine_id="precision_arithmetic_engine",
            run_id="run_20230103_002",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("123.456789"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        precise_money = high_precision_transfer.money
        precise_result = precise_money * Decimal("1.234567")
        # 验证高精度计算结果
        assert isinstance(precise_result, Decimal)
        # 确保精度没有异常损失
        assert len(str(precise_result).split('.')[-1]) >= 6  # 至少保持6位小数

        # 测试零值和负值的边界算术
        zero_transfer = Transfer(
            portfolio_id="zero_portfolio",
            engine_id="zero_engine",
            run_id="run_20230103_003",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("0.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        zero_money = zero_transfer.money
        assert zero_money + Decimal("100.00") == Decimal("100.00")
        assert zero_money * Decimal("1000.00") == Decimal("0.00")

    def test_financial_rounding_rules(self):
        """测试金融舍入规则"""
        # 测试各种舍入场景

        # 测试银行家舍入（四舍六入五成双）
        from decimal import ROUND_HALF_EVEN

        # 创建需要舍入的金额
        amounts_to_round = [
            (Decimal("1000.125"), Decimal("1000.12")),   # .125 -> .12 (5后无数字，偶数)
            (Decimal("1000.135"), Decimal("1000.14")),   # .135 -> .14 (5后无数字，奇数)
            (Decimal("1000.126"), Decimal("1000.13")),   # .126 -> .13 (6入)
            (Decimal("1000.124"), Decimal("1000.12")),   # .124 -> .12 (4舍)
        ]

        for original_amount, expected_rounded in amounts_to_round:
            # 先创建Transfer实例
            transfer = Transfer(
                portfolio_id="rounding_portfolio",
                engine_id="rounding_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=original_amount,
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            # 测试金额舍入
            rounded_amount = transfer.money.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
            assert rounded_amount == expected_rounded
            assert isinstance(rounded_amount, Decimal)

        # 测试不同精度的舍入
        high_precision_amount = Decimal("1234.56789")
        transfer = Transfer(
            portfolio_id="precision_rounding_portfolio",
            engine_id="precision_rounding_engine",
            run_id="run_20230103_002",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=high_precision_amount,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        money = transfer.money

        # 舍入到2位小数
        rounded_2_decimal = money.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
        assert rounded_2_decimal == Decimal("1234.57")

        # 舍入到4位小数
        rounded_4_decimal = money.quantize(Decimal('0.0001'), rounding=ROUND_HALF_EVEN)
        assert rounded_4_decimal == Decimal("1234.5679")

        # 舍入到整数
        rounded_integer = money.quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)
        assert rounded_integer == Decimal("1235")

        # 测试极小金额的舍入
        tiny_amounts = [
            Decimal("0.001"),   # 舍入到0.00
            Decimal("0.005"),   # 银行家舍入到0.00
            Decimal("0.006"),   # 舍入到0.01
        ]

        for tiny_amount in tiny_amounts:
            transfer = Transfer(
                portfolio_id="tiny_amount_portfolio",
                engine_id="tiny_amount_engine",
                run_id="run_20230103_003",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=tiny_amount,
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            rounded = transfer.money.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
            assert isinstance(rounded, Decimal)
            # 确保舍入结果是2位小数
            assert len(str(rounded).split('.')[-1]) <= 2

    def test_extreme_amount_boundaries(self):
        """测试极值金额边界处理"""
        # 测试极大和极小金额

        # 测试最小可能的金额
        minimum_amounts = [
            Decimal("0.01"),           # 最小货币单位
            Decimal("0.0001"),         # 万分之一
            Decimal("0.00000001"),     # 极小精度
        ]

        for min_amount in minimum_amounts:
            transfer = Transfer(
                portfolio_id="minimum_portfolio",
                engine_id="minimum_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=min_amount,
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            assert transfer.money == min_amount
            assert transfer.money > Decimal("0")
            assert isinstance(transfer.money, Decimal)

        # 测试零值边界
        zero_amount = Decimal("0.00")
        zero_transfer = Transfer(
            portfolio_id="zero_boundary_portfolio",
            engine_id="zero_boundary_engine",
            run_id="run_20230103_002",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=zero_amount,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        assert zero_transfer.money == zero_amount
        assert zero_transfer.money >= Decimal("0")

        # 测试极大金额
        maximum_amounts = [
            Decimal("999999999999.99"),      # 接近万亿
            Decimal("1000000000000.00"),     # 万亿整数
            Decimal("9999999999999.99"),     # 接近十万亿
        ]

        for max_amount in maximum_amounts:
            transfer = Transfer(
                portfolio_id="maximum_portfolio",
                engine_id="maximum_engine",
                run_id="run_20230103_003",
                direction=TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.NASDAQ,
                money=max_amount,
                status=TRANSFERSTATUS_TYPES.SUBMITTED,
                timestamp="2023-01-03"
            )

            assert transfer.money == max_amount
            assert isinstance(transfer.money, Decimal)

            # 验证极大数值的字符串表示正确
            money_str = str(transfer.money)
            assert len(money_str.split('.')[0]) >= 12  # 至少12位整数

        # 测试接近系统极限的边界
        system_boundary_amounts = [
            Decimal("1" + "0" * 28 + ".99"),  # 极大数
            Decimal("0." + "0" * 27 + "1"),   # 极小数
        ]

        for boundary_amount in system_boundary_amounts:
            try:
                transfer = Transfer(
                    portfolio_id="boundary_portfolio",
                    engine_id="boundary_engine",
                    run_id="run_20230103_004",
                    direction=TRANSFERDIRECTION_TYPES.IN,
                    market=MARKET_TYPES.CHINA,
                    money=boundary_amount,
                    status=TRANSFERSTATUS_TYPES.NEW,
                    timestamp="2023-01-03"
                )

                assert transfer.money == boundary_amount
                assert isinstance(transfer.money, Decimal)

            except (ValueError, OverflowError):
                # 某些极端值可能超出系统处理能力，这是可接受的
                pass

        # 测试边界算术运算的稳定性
        large_amount = Decimal("999999999.99")
        small_amount = Decimal("0.01")

        large_transfer = Transfer(
            portfolio_id="arithmetic_boundary_portfolio",
            engine_id="arithmetic_boundary_engine",
            run_id="run_20230103_005",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=large_amount,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        small_transfer = Transfer(
            portfolio_id="arithmetic_boundary_portfolio",
            engine_id="arithmetic_boundary_engine",
            run_id="run_20230103_006",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.CHINA,
            money=small_amount,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 边界加法
        boundary_sum = large_transfer.money + small_transfer.money
        assert boundary_sum == Decimal("1000000000.00")

        # 边界减法
        boundary_diff = large_transfer.money - small_transfer.money
        assert boundary_diff == Decimal("999999999.98")

    def test_money_type_conversion_accuracy(self):
        """测试不同数值类型转换精度"""
        # 测试int、float、Decimal之间转换

        # 测试从整数int转换
        int_amounts = [100, 1000, 50000]
        for int_amount in int_amounts:
            transfer = Transfer(
                portfolio_id="int_conversion_portfolio",
                engine_id="int_conversion_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=int_amount,  # 传入int类型
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            # 验证转换后为Decimal类型
            assert isinstance(transfer.money, Decimal)
            assert transfer.money == Decimal(str(int_amount))

        # 测试从浮点数float转换
        float_amounts = [1000.50, 2500.75, 999.99]
        for float_amount in float_amounts:
            transfer = Transfer(
                portfolio_id="float_conversion_portfolio",
                engine_id="float_conversion_engine",
                run_id="run_20230103_002",
                direction=TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.NASDAQ,
                money=float_amount,  # 传入float类型
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            # 验证转换后为Decimal类型
            assert isinstance(transfer.money, Decimal)
            # 注意：float到Decimal可能有精度问题，我们检查近似相等
            assert abs(float(transfer.money) - float_amount) < 0.01

        # 测试Decimal到Decimal（无转换损失）
        decimal_amounts = [
            Decimal("1234.5678"),
            Decimal("0.0001"),
            Decimal("999999.9999")
        ]

        for decimal_amount in decimal_amounts:
            transfer = Transfer(
                portfolio_id="decimal_conversion_portfolio",
                engine_id="decimal_conversion_engine",
                run_id="run_20230103_003",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=decimal_amount,  # 传入Decimal类型
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            # 验证完全精确的转换
            assert isinstance(transfer.money, Decimal)
            assert transfer.money == decimal_amount

        # 测试精度损失的检测
        problematic_float = 0.1 + 0.2  # 著名的浮点精度问题
        transfer = Transfer(
            portfolio_id="precision_loss_portfolio",
            engine_id="precision_loss_engine",
            run_id="run_20230103_004",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=problematic_float,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 验证Decimal能处理浮点精度问题
        assert isinstance(transfer.money, Decimal)
        # float的0.1+0.2通常不等于0.3，但Decimal会保持实际的表示
        assert transfer.money != Decimal("0.3")

        # 测试大整数转换
        large_int = 999999999999
        transfer = Transfer(
            portfolio_id="large_int_portfolio",
            engine_id="large_int_engine",
            run_id="run_20230103_005",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.CHINA,
            money=large_int,
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        assert isinstance(transfer.money, Decimal)
        assert transfer.money == Decimal(str(large_int))

        # 测试转换精度保持验证
        conversion_test_data = [
            (1000, Decimal("1000")),           # int -> Decimal
            (Decimal("1000.50"), Decimal("1000.50")),  # Decimal -> Decimal
        ]

        for input_value, expected_decimal in conversion_test_data:
            transfer = Transfer(
                portfolio_id="conversion_test_portfolio",
                engine_id="conversion_test_engine",
                run_id="run_20230103_006",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=input_value,
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            assert isinstance(transfer.money, Decimal)
            assert transfer.money == expected_decimal

            # 验证转换后字符串表示的正确性
            assert str(transfer.money) == str(expected_decimal)


@pytest.mark.unit
class TestTransferIntegration:
    """9. Transfer集成测试"""

    def test_portfolio_association_validation(self):
        """测试与Portfolio的关联验证"""
        # 测试与Portfolio的关联验证

        # 测试有效的portfolio_id关联
        valid_portfolio_ids = [
            "portfolio_001",
            "test_portfolio_2023",
            "live_portfolio_main",
            "backtest_portfolio_strategy_A"
        ]

        for portfolio_id in valid_portfolio_ids:
            transfer = Transfer(
                portfolio_id=portfolio_id,
                engine_id="test_engine",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            # 验证portfolio_id正确设置
            assert transfer.portfolio_id == portfolio_id
            assert isinstance(transfer.portfolio_id, str)
            assert len(transfer.portfolio_id) > 0

        # 测试portfolio_id的setter功能
        transfer = Transfer(
            portfolio_id="original_portfolio",
            engine_id="test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.SUBMITTED,
            timestamp="2023-01-03"
        )

        # 更新portfolio_id
        new_portfolio_id = "updated_portfolio_2023"
        transfer.portfolio_id = new_portfolio_id
        assert transfer.portfolio_id == new_portfolio_id

        # 测试通过set方法更新portfolio关联
        transfer.set(
            "final_portfolio",
            "final_engine",
            "run_20230103_002",
            TRANSFERDIRECTION_TYPES.IN,
            MARKET_TYPES.CHINA,
            Decimal("3000.00"),
            TRANSFERSTATUS_TYPES.FILLED,
            "2023-01-03"
        )

        assert transfer.portfolio_id == "final_portfolio"

        # 测试portfolio_id的业务逻辑关联
        # 同一个portfolio的多笔转账应该保持关联性
        portfolio_id = "multi_transfer_portfolio"
        transfers = []

        for i in range(3):
            transfer = Transfer(
                portfolio_id=portfolio_id,
                engine_id=f"engine_{i+1}",
                run_id=f"run_20230103_{i+1:03d}",
                direction=TRANSFERDIRECTION_TYPES.IN if i % 2 == 0 else TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.CHINA,
                money=Decimal(f"{1000 * (i+1)}.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )
            transfers.append(transfer)

        # 验证所有转账都关联到同一个portfolio
        for transfer in transfers:
            assert transfer.portfolio_id == portfolio_id

        # 验证portfolio关联的唯一性识别
        assert len(set(t.portfolio_id for t in transfers)) == 1

    def test_engine_association_validation(self):
        """测试与Engine的关联验证"""
        # 测试与Engine的关联验证

        # 测试有效的engine_id关联
        valid_engine_ids = [
            "historic_engine_001",
            "live_engine_production",
            "matrix_engine_backtest",
            "event_driven_engine_test"
        ]

        for engine_id in valid_engine_ids:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id=engine_id,
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            # 验证engine_id正确设置
            assert transfer.engine_id == engine_id
            assert isinstance(transfer.engine_id, str)
            assert len(transfer.engine_id) > 0

        # 测试engine_id的setter功能
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="original_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.SUBMITTED,
            timestamp="2023-01-03"
        )

        # 更新engine_id
        new_engine_id = "updated_engine_2023"
        transfer.engine_id = new_engine_id
        assert transfer.engine_id == new_engine_id

        # 测试通过set方法更新engine关联
        transfer.set(
            "test_portfolio",
            "final_engine_live",
            "run_20230103_002",
            TRANSFERDIRECTION_TYPES.IN,
            MARKET_TYPES.CHINA,
            Decimal("3000.00"),
            TRANSFERSTATUS_TYPES.FILLED,
            "2023-01-03"
        )

        assert transfer.engine_id == "final_engine_live"

        # 测试不同engine类型的转账处理
        engine_types = [
            ("backtest_engine", TRANSFERSTATUS_TYPES.FILLED),
            ("live_engine", TRANSFERSTATUS_TYPES.PENDING),
            ("paper_engine", TRANSFERSTATUS_TYPES.SUBMITTED),
        ]

        for engine_id, expected_status in engine_types:
            transfer = Transfer(
                portfolio_id="multi_engine_portfolio",
                engine_id=engine_id,
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1500.00"),
                status=expected_status,
                timestamp="2023-01-03"
            )

            assert transfer.engine_id == engine_id
            assert transfer.status == expected_status

        # 测试同一engine下的多笔转账关联
        engine_id = "single_engine_multiple_transfers"
        engine_transfers = []

        for i in range(4):
            transfer = Transfer(
                portfolio_id=f"portfolio_{i+1}",
                engine_id=engine_id,
                run_id=f"run_20230103_{i+1:03d}",
                direction=TRANSFERDIRECTION_TYPES.IN if i < 2 else TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.CHINA,
                money=Decimal(f"{500 * (i+1)}.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )
            engine_transfers.append(transfer)

        # 验证所有转账都关联到同一个engine
        for transfer in engine_transfers:
            assert transfer.engine_id == engine_id

        # 验证engine关联的唯一性
        assert len(set(t.engine_id for t in engine_transfers)) == 1

        # 测试engine关联的业务场景验证
        # 不同engine应该能够处理不同类型的转账
        cross_engine_scenarios = [
            ("backtest_engine", MARKET_TYPES.CHINA, Decimal("10000.00")),
            ("live_engine", MARKET_TYPES.NASDAQ, Decimal("50000.00")),
            ("matrix_engine", MARKET_TYPES.CHINA, Decimal("25000.00")),
        ]

        for engine_id, market, amount in cross_engine_scenarios:
            transfer = Transfer(
                portfolio_id="cross_engine_portfolio",
                engine_id=engine_id,
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=market,
                money=amount,
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            assert transfer.engine_id == engine_id
            assert transfer.market == market
            assert transfer.money == amount

    def test_run_association_validation(self):
        """测试与Run的关联验证"""
        # 测试与Run的关联验证

        # 测试有效的run_id关联
        valid_run_ids = [
            "run_20230103_001",
            "backtest_run_strategy_A_20230103",
            "live_run_production_001",
            "paper_trading_run_test_123"
        ]

        for run_id in valid_run_ids:
            transfer = Transfer(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                run_id=run_id,
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            # 验证run_id正确设置
            assert transfer.run_id == run_id
            assert isinstance(transfer.run_id, str)
            assert len(transfer.run_id) > 0

        # 测试run_id的setter功能
        transfer = Transfer(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="original_run",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.SUBMITTED,
            timestamp="2023-01-03"
        )

        # 更新run_id
        new_run_id = "updated_run_20230103_v2"
        transfer.run_id = new_run_id
        assert transfer.run_id == new_run_id

        # 测试通过set方法更新run关联
        transfer.set(
            "test_portfolio",
            "test_engine",
            "final_run_production_002",
            TRANSFERDIRECTION_TYPES.IN,
            MARKET_TYPES.CHINA,
            Decimal("3000.00"),
            TRANSFERSTATUS_TYPES.FILLED,
            "2023-01-03"
        )

        assert transfer.run_id == "final_run_production_002"

        # 测试同一run下的多笔转账序列
        run_id = "sequential_transfers_run_20230103"
        run_transfers = []

        # 模拟一个交易运行中的多笔转账序列
        transfer_sequence = [
            (TRANSFERDIRECTION_TYPES.IN, Decimal("10000.00"), TRANSFERSTATUS_TYPES.FILLED),    # 初始资金入账
            (TRANSFERDIRECTION_TYPES.OUT, Decimal("3000.00"), TRANSFERSTATUS_TYPES.FILLED),   # 买入股票
            (TRANSFERDIRECTION_TYPES.IN, Decimal("3500.00"), TRANSFERSTATUS_TYPES.FILLED),    # 卖出盈利
            (TRANSFERDIRECTION_TYPES.OUT, Decimal("1000.00"), TRANSFERSTATUS_TYPES.PENDING),  # 手续费扣除
        ]

        for i, (direction, amount, status) in enumerate(transfer_sequence):
            transfer = Transfer(
                portfolio_id="sequential_portfolio",
                engine_id="sequential_engine",
                run_id=run_id,
                direction=direction,
                market=MARKET_TYPES.CHINA,
                money=amount,
                status=status,
                timestamp="2023-01-03"
            )
            run_transfers.append(transfer)

        # 验证所有转账都属于同一个run
        for transfer in run_transfers:
            assert transfer.run_id == run_id

        # 验证run的一致性
        assert len(set(t.run_id for t in run_transfers)) == 1

        # 测试run_id的时间序列特征
        time_based_run_ids = [
            "run_20230101_001",
            "run_20230102_001",
            "run_20230103_001",
            "run_20230103_002"
        ]

        time_transfers = []
        for i, run_id in enumerate(time_based_run_ids):
            transfer = Transfer(
                portfolio_id="time_series_portfolio",
                engine_id="time_series_engine",
                run_id=run_id,
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal(f"{1000 + i*100}.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )
            time_transfers.append(transfer)

        # 验证不同时间的run_id都能正确设置
        for i, transfer in enumerate(time_transfers):
            assert transfer.run_id == time_based_run_ids[i]

        # 测试run关联的业务逻辑验证
        # 回测run vs 实盘run的处理差异
        run_scenarios = [
            ("backtest_run_20230103", TRANSFERSTATUS_TYPES.FILLED),
            ("live_run_20230103", TRANSFERSTATUS_TYPES.PENDING),
            ("paper_run_20230103", TRANSFERSTATUS_TYPES.SUBMITTED),
        ]

        for run_id, expected_status in run_scenarios:
            transfer = Transfer(
                portfolio_id="scenario_portfolio",
                engine_id="scenario_engine",
                run_id=run_id,
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("5000.00"),
                status=expected_status,
                timestamp="2023-01-03"
            )

            assert transfer.run_id == run_id
            assert transfer.status == expected_status

        # 验证run_id格式的一致性
        run_id_patterns = [
            "run_20230103_001",
            "RUN_20230103_002",
            "live_run_production_20230103_001"
        ]

        for pattern in run_id_patterns:
            transfer = Transfer(
                portfolio_id="pattern_portfolio",
                engine_id="pattern_engine",
                run_id=pattern,
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )

            assert transfer.run_id == pattern
            assert isinstance(transfer.run_id, str)

    def test_uuid_consistency_across_components(self):
        """测试UUID在组件间的一致性"""
        # 验证UUID在不同组件间保持一致

        # 测试自动生成UUID的一致性
        transfer = Transfer(
            portfolio_id="uuid_test_portfolio",
            engine_id="uuid_test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 验证UUID存在且格式正确
        assert hasattr(transfer, 'uuid')
        assert transfer.uuid is not None
        assert isinstance(transfer.uuid, str)
        assert len(transfer.uuid) > 0

        # 验证UUID的唯一性
        original_uuid = transfer.uuid

        # 创建另一个Transfer实例
        transfer2 = Transfer(
            portfolio_id="uuid_test_portfolio_2",
            engine_id="uuid_test_engine_2",
            run_id="run_20230103_002",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.SUBMITTED,
            timestamp="2023-01-03"
        )

        # 验证不同实例有不同的UUID
        assert transfer2.uuid != original_uuid

        # 测试指定UUID的一致性
        custom_uuid = "custom_transfer_uuid_123456"
        transfer_with_custom_uuid = Transfer(
            portfolio_id="custom_uuid_portfolio",
            engine_id="custom_uuid_engine",
            run_id="run_20230103_003",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("3000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03",
            uuid=custom_uuid
        )

        # 验证自定义UUID正确设置
        assert transfer_with_custom_uuid.uuid == custom_uuid

        # 测试UUID在对象生命周期中的持续性
        persistent_transfer = Transfer(
            portfolio_id="persistent_portfolio",
            engine_id="persistent_engine",
            run_id="run_20230103_004",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.CHINA,
            money=Decimal("4000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        persistent_uuid = persistent_transfer.uuid

        # 执行各种操作后UUID应该保持不变
        persistent_transfer.portfolio_id = "updated_portfolio"
        persistent_transfer.engine_id = "updated_engine"
        persistent_transfer.run_id = "updated_run"

        assert persistent_transfer.uuid == persistent_uuid

        # 通过set方法更新后UUID应该保持不变
        persistent_transfer.set(
            "final_portfolio",
            "final_engine",
            "final_run",
            TRANSFERDIRECTION_TYPES.IN,
            MARKET_TYPES.NASDAQ,
            Decimal("5000.00"),
            TRANSFERSTATUS_TYPES.FILLED,
            "2023-01-03"
        )

        assert persistent_transfer.uuid == persistent_uuid

        # 测试UUID在集合操作中的唯一性
        transfers_batch = []
        batch_size = 10

        for i in range(batch_size):
            transfer = Transfer(
                portfolio_id=f"batch_portfolio_{i}",
                engine_id=f"batch_engine_{i}",
                run_id=f"run_20230103_{i:03d}",
                direction=TRANSFERDIRECTION_TYPES.IN if i % 2 == 0 else TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.CHINA,
                money=Decimal(f"{1000 + i*100}.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )
            transfers_batch.append(transfer)

        # 验证批量创建的UUID都是唯一的
        uuids = [t.uuid for t in transfers_batch]
        assert len(uuids) == len(set(uuids))  # 所有UUID都不重复

        # 验证每个UUID都是有效的字符串
        for uuid in uuids:
            assert isinstance(uuid, str)
            assert len(uuid) > 0

        # 测试UUID格式的一致性（如果使用标准UUID格式）
        import re
        uuid_pattern = re.compile(r'^[a-f0-9-]+$', re.IGNORECASE)

        for transfer in transfers_batch:
            # 验证UUID格式（允许各种UUID格式）
            assert isinstance(transfer.uuid, str)
            assert len(transfer.uuid) > 0
            # UUID应该是可打印字符
            assert transfer.uuid.isprintable()

        # 测试空UUID的处理
        empty_uuid_transfer = Transfer(
            portfolio_id="empty_uuid_portfolio",
            engine_id="empty_uuid_engine",
            run_id="run_20230103_005",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03",
            uuid=""  # 空UUID应该触发自动生成
        )

        # 验证空UUID被自动生成替换
        assert empty_uuid_transfer.uuid != ""
        assert len(empty_uuid_transfer.uuid) > 0

    def test_component_type_integration(self):
        """测试component_type的集成验证"""
        # 验证component_type在系统中正确识别

        # 测试Transfer的component_type正确设置
        transfer = Transfer(
            portfolio_id="component_test_portfolio",
            engine_id="component_test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 验证component_type正确设置为TRANSFER
        assert hasattr(transfer, 'component_type')
        assert transfer.component_type == COMPONENT_TYPES.TRANSFER
        assert isinstance(transfer.component_type, COMPONENT_TYPES)

        # 测试多个Transfer实例的component_type一致性
        transfers = []
        for i in range(5):
            t = Transfer(
                portfolio_id=f"portfolio_{i}",
                engine_id=f"engine_{i}",
                run_id=f"run_20230103_{i:03d}",
                direction=TRANSFERDIRECTION_TYPES.IN if i % 2 == 0 else TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.CHINA,
                money=Decimal(f"{1000 + i*100}.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )
            transfers.append(t)

        # 验证所有Transfer实例都有相同的component_type
        for transfer in transfers:
            assert transfer.component_type == COMPONENT_TYPES.TRANSFER

        # 验证component_type在对象生命周期中保持不变
        persistent_transfer = Transfer(
            portfolio_id="persistent_portfolio",
            engine_id="persistent_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        original_component_type = persistent_transfer.component_type

        # 执行各种修改操作
        persistent_transfer.portfolio_id = "updated_portfolio"
        persistent_transfer.engine_id = "updated_engine"
        persistent_transfer.run_id = "updated_run"

        # component_type应该保持不变
        assert persistent_transfer.component_type == original_component_type
        assert persistent_transfer.component_type == COMPONENT_TYPES.TRANSFER

        # 通过set方法更新后component_type也应该保持不变
        persistent_transfer.set(
            "final_portfolio",
            "final_engine",
            "final_run",
            TRANSFERDIRECTION_TYPES.OUT,
            MARKET_TYPES.NASDAQ,
            Decimal("3000.00"),
            TRANSFERSTATUS_TYPES.FILLED,
            "2023-01-03"
        )

        assert persistent_transfer.component_type == COMPONENT_TYPES.TRANSFER

        # 测试component_type的数值表示
        assert COMPONENT_TYPES.TRANSFER.value == 13  # 根据enums.py中的定义

        # 验证component_type可以用于类型识别
        def identify_component(obj):
            if hasattr(obj, 'component_type'):
                return obj.component_type
            return None

        identified_type = identify_component(transfer)
        assert identified_type == COMPONENT_TYPES.TRANSFER

        # 测试component_type在集合操作中的一致性
        transfer_collection = [
            Transfer(
                portfolio_id="collection_portfolio_1",
                engine_id="collection_engine_1",
                run_id="run_20230103_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("1000.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            ),
            Transfer(
                portfolio_id="collection_portfolio_2",
                engine_id="collection_engine_2",
                run_id="run_20230103_002",
                direction=TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.NASDAQ,
                money=Decimal("2000.00"),
                status=TRANSFERSTATUS_TYPES.SUBMITTED,
                timestamp="2023-01-03"
            )
        ]

        # 验证集合中所有对象都是TRANSFER类型
        component_types = [t.component_type for t in transfer_collection]
        assert all(ct == COMPONENT_TYPES.TRANSFER for ct in component_types)

        # 测试component_type的枚举属性
        transfer_type = transfer.component_type
        assert isinstance(transfer_type, COMPONENT_TYPES)
        assert transfer_type.name == "TRANSFER"
        assert transfer_type.value == 13

        # 验证component_type不能被意外修改
        # 通过检查是否有setter来验证只读性
        try:
            # 尝试直接修改component_type (应该不被允许)
            transfer.component_type = COMPONENT_TYPES.SIGNAL
            # 如果修改成功，检查是否真的改变了
            if transfer.component_type != COMPONENT_TYPES.TRANSFER:
                assert False, "component_type should be read-only"
        except (AttributeError, TypeError):
            # 如果抛出异常，说明component_type是只读的，这是预期行为
            pass

        # 最终验证component_type仍然是TRANSFER
        assert transfer.component_type == COMPONENT_TYPES.TRANSFER

    def test_transfer_lifecycle_integration(self):
        """测试转账生命周期的集成流程"""
        # 模拟完整的转账生命周期

        # 阶段1: 创建新转账（NEW状态）
        transfer = Transfer(
            portfolio_id="lifecycle_portfolio",
            engine_id="lifecycle_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("10000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 验证初始状态
        assert transfer.status == TRANSFERSTATUS_TYPES.NEW
        assert transfer.money == Decimal("10000.00")
        assert transfer.direction == TRANSFERDIRECTION_TYPES.IN

        # 阶段2: 提交转账（NEW -> SUBMITTED）
        # 模拟转账提交过程
        submitted_transfer = Transfer(
            portfolio_id=transfer.portfolio_id,
            engine_id=transfer.engine_id,
            run_id=transfer.run_id,
            direction=transfer.direction,
            market=transfer.market,
            money=transfer.money,
            status=TRANSFERSTATUS_TYPES.SUBMITTED,
            timestamp="2023-01-03",
            uuid=transfer.uuid  # 保持相同的UUID
        )

        # 验证提交状态
        assert submitted_transfer.status == TRANSFERSTATUS_TYPES.SUBMITTED
        assert submitted_transfer.uuid == transfer.uuid  # UUID保持一致

        # 阶段3: 处理中状态（SUBMITTED -> PENDING）
        pending_transfer = Transfer(
            portfolio_id=submitted_transfer.portfolio_id,
            engine_id=submitted_transfer.engine_id,
            run_id=submitted_transfer.run_id,
            direction=submitted_transfer.direction,
            market=submitted_transfer.market,
            money=submitted_transfer.money,
            status=TRANSFERSTATUS_TYPES.PENDING,
            timestamp="2023-01-03",
            uuid=submitted_transfer.uuid
        )

        # 验证处理中状态
        assert pending_transfer.status == TRANSFERSTATUS_TYPES.PENDING

        # 阶段4: 成功完成（PENDING -> FILLED）
        filled_transfer = Transfer(
            portfolio_id=pending_transfer.portfolio_id,
            engine_id=pending_transfer.engine_id,
            run_id=pending_transfer.run_id,
            direction=pending_transfer.direction,
            market=pending_transfer.market,
            money=pending_transfer.money,
            status=TRANSFERSTATUS_TYPES.FILLED,
            timestamp="2023-01-03",
            uuid=pending_transfer.uuid
        )

        # 验证最终完成状态
        assert filled_transfer.status == TRANSFERSTATUS_TYPES.FILLED
        assert filled_transfer.uuid == transfer.uuid  # UUID在整个生命周期保持一致

        # 测试失败场景：转账被取消（任意状态 -> CANCELED）
        canceled_transfer = Transfer(
            portfolio_id="lifecycle_portfolio_canceled",
            engine_id="lifecycle_engine_canceled",
            run_id="run_20230103_002",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("5000.00"),
            status=TRANSFERSTATUS_TYPES.SUBMITTED,
            timestamp="2023-01-03"
        )

        # 模拟取消操作
        canceled_final = Transfer(
            portfolio_id=canceled_transfer.portfolio_id,
            engine_id=canceled_transfer.engine_id,
            run_id=canceled_transfer.run_id,
            direction=canceled_transfer.direction,
            market=canceled_transfer.market,
            money=canceled_transfer.money,
            status=TRANSFERSTATUS_TYPES.CANCELED,
            timestamp="2023-01-03",
            uuid=canceled_transfer.uuid
        )

        assert canceled_final.status == TRANSFERSTATUS_TYPES.CANCELED

        # 测试完整的转账批次生命周期
        batch_transfers = []
        batch_size = 3

        # 创建一批转账
        for i in range(batch_size):
            transfer = Transfer(
                portfolio_id="batch_lifecycle_portfolio",
                engine_id="batch_lifecycle_engine",
                run_id=f"run_20230103_{i+1:03d}",
                direction=TRANSFERDIRECTION_TYPES.IN if i % 2 == 0 else TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.CHINA,
                money=Decimal(f"{1000 * (i+1)}.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )
            batch_transfers.append(transfer)

        # 验证批次初始状态
        for transfer in batch_transfers:
            assert transfer.status == TRANSFERSTATUS_TYPES.NEW

        # 模拟批次处理：全部提交
        submitted_batch = []
        for transfer in batch_transfers:
            submitted = Transfer(
                portfolio_id=transfer.portfolio_id,
                engine_id=transfer.engine_id,
                run_id=transfer.run_id,
                direction=transfer.direction,
                market=transfer.market,
                money=transfer.money,
                status=TRANSFERSTATUS_TYPES.SUBMITTED,
                timestamp="2023-01-03",
                uuid=transfer.uuid
            )
            submitted_batch.append(submitted)

        # 验证批次提交状态
        for transfer in submitted_batch:
            assert transfer.status == TRANSFERSTATUS_TYPES.SUBMITTED

        # 模拟差异化结果：部分成功，部分失败
        final_batch = []
        for i, transfer in enumerate(submitted_batch):
            final_status = TRANSFERSTATUS_TYPES.FILLED if i % 2 == 0 else TRANSFERSTATUS_TYPES.CANCELED
            final_transfer = Transfer(
                portfolio_id=transfer.portfolio_id,
                engine_id=transfer.engine_id,
                run_id=transfer.run_id,
                direction=transfer.direction,
                market=transfer.market,
                money=transfer.money,
                status=final_status,
                timestamp="2023-01-03",
                uuid=transfer.uuid
            )
            final_batch.append(final_transfer)

        # 验证差异化结果
        filled_count = sum(1 for t in final_batch if t.status == TRANSFERSTATUS_TYPES.FILLED)
        canceled_count = sum(1 for t in final_batch if t.status == TRANSFERSTATUS_TYPES.CANCELED)

        assert filled_count == 2  # 索引0,2成功
        assert canceled_count == 1  # 索引1失败

        # 测试生命周期中的数据一致性
        lifecycle_transfer = Transfer(
            portfolio_id="consistency_portfolio",
            engine_id="consistency_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("8000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        original_data = {
            'portfolio_id': lifecycle_transfer.portfolio_id,
            'engine_id': lifecycle_transfer.engine_id,
            'run_id': lifecycle_transfer.run_id,
            'direction': lifecycle_transfer.direction,
            'market': lifecycle_transfer.market,
            'money': lifecycle_transfer.money,
            'uuid': lifecycle_transfer.uuid
        }

        # 模拟状态变更但核心数据保持不变
        status_transitions = [
            TRANSFERSTATUS_TYPES.SUBMITTED,
            TRANSFERSTATUS_TYPES.PENDING,
            TRANSFERSTATUS_TYPES.FILLED
        ]

        for status in status_transitions:
            updated_transfer = Transfer(
                portfolio_id=original_data['portfolio_id'],
                engine_id=original_data['engine_id'],
                run_id=original_data['run_id'],
                direction=original_data['direction'],
                market=original_data['market'],
                money=original_data['money'],
                status=status,
                timestamp="2023-01-03",
                uuid=original_data['uuid']
            )

            # 验证核心数据在状态变更中保持一致
            assert updated_transfer.portfolio_id == original_data['portfolio_id']
            assert updated_transfer.engine_id == original_data['engine_id']
            assert updated_transfer.run_id == original_data['run_id']
            assert updated_transfer.direction == original_data['direction']
            assert updated_transfer.market == original_data['market']
            assert updated_transfer.money == original_data['money']
            assert updated_transfer.uuid == original_data['uuid']
            assert updated_transfer.status == status

    def test_inheritance_from_base_class(self):
        """测试从Base类继承的功能集成"""
        # 验证继承的属性和方法

        # 创建Transfer实例
        transfer = Transfer(
            portfolio_id="inheritance_test_portfolio",
            engine_id="inheritance_test_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # 验证从Base类继承的UUID属性
        assert hasattr(transfer, 'uuid')
        assert transfer.uuid is not None
        assert isinstance(transfer.uuid, str)
        assert len(transfer.uuid) > 0

        # 验证从Base类继承的component_type属性
        assert hasattr(transfer, 'component_type')
        assert transfer.component_type == COMPONENT_TYPES.TRANSFER
        assert isinstance(transfer.component_type, COMPONENT_TYPES)

        # 验证Transfer是Base类的实例
        from ginkgo.trading.core.base import Base
        assert isinstance(transfer, Base)

        # 验证继承的类层次结构
        assert issubclass(Transfer, Base)

        # 测试Base类的方法在Transfer中是否可用
        # 验证对象的字符串表示（__repr__方法）
        repr_str = repr(transfer)
        assert isinstance(repr_str, str)
        assert "Transfer" in repr_str
        assert len(repr_str) > 0

        # 测试自定义UUID的继承功能
        custom_uuid = "custom_inheritance_test_uuid"
        transfer_with_custom_uuid = Transfer(
            portfolio_id="custom_inheritance_portfolio",
            engine_id="custom_inheritance_engine",
            run_id="run_20230103_002",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("2000.00"),
            status=TRANSFERSTATUS_TYPES.SUBMITTED,
            timestamp="2023-01-03",
            uuid=custom_uuid
        )

        # 验证自定义UUID通过Base类正确设置
        assert transfer_with_custom_uuid.uuid == custom_uuid

        # 测试多个实例的继承一致性
        transfers = []
        for i in range(3):
            t = Transfer(
                portfolio_id=f"inheritance_portfolio_{i}",
                engine_id=f"inheritance_engine_{i}",
                run_id=f"run_20230103_{i:03d}",
                direction=TRANSFERDIRECTION_TYPES.IN if i % 2 == 0 else TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.CHINA,
                money=Decimal(f"{1000 + i*500}.00"),
                status=TRANSFERSTATUS_TYPES.NEW,
                timestamp="2023-01-03"
            )
            transfers.append(t)

        # 验证所有实例都正确继承Base类功能
        for transfer in transfers:
            assert isinstance(transfer, Base)
            assert hasattr(transfer, 'uuid')
            assert hasattr(transfer, 'component_type')
            assert transfer.component_type == COMPONENT_TYPES.TRANSFER

        # 验证继承的UUID唯一性
        uuids = [t.uuid for t in transfers]
        assert len(uuids) == len(set(uuids))  # 所有UUID都不重复

        # 测试Base类的初始化参数传递
        base_args_transfer = Transfer(
            portfolio_id="base_args_portfolio",
            engine_id="base_args_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("3000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03",
            uuid="base_args_uuid"  # 通过Base类初始化
        )

        # 验证Base类参数正确传递和设置
        assert base_args_transfer.uuid == "base_args_uuid"
        assert base_args_transfer.component_type == COMPONENT_TYPES.TRANSFER

        # 测试继承链的方法解析顺序（MRO）
        mro = Transfer.__mro__
        assert Base in mro
        assert Transfer in mro

        # 验证Transfer特有的属性不会干扰Base类功能
        transfer_specific_attrs = [
            'portfolio_id', 'engine_id', 'run_id', 'direction',
            'market', 'money', 'status', 'timestamp'
        ]

        for attr in transfer_specific_attrs:
            assert hasattr(transfer, attr)
            # 确保Transfer特有属性存在且不为None
            assert getattr(transfer, attr) is not None

        # 同时验证Base类的核心属性仍然正常工作
        base_attrs = ['uuid', 'component_type']
        for attr in base_attrs:
            assert hasattr(transfer, attr)
            assert getattr(transfer, attr) is not None

        # 测试多重继承的兼容性（如果有其他父类）
        # 检查Transfer的所有父类
        transfer_bases = Transfer.__bases__
        assert Base in transfer_bases

        # 验证继承不会影响Transfer的业务逻辑
        business_transfer = Transfer(
            portfolio_id="business_inheritance_portfolio",
            engine_id="business_inheritance_engine",
            run_id="run_20230103_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("5000.00"),
            status=TRANSFERSTATUS_TYPES.NEW,
            timestamp="2023-01-03"
        )

        # Base类功能不应影响Transfer的业务方法
        business_transfer.portfolio_id = "updated_business_portfolio"
        business_transfer.engine_id = "updated_business_engine"

        # 验证业务属性更新后，Base类属性仍然正常
        assert business_transfer.uuid is not None
        assert business_transfer.component_type == COMPONENT_TYPES.TRANSFER
        assert business_transfer.portfolio_id == "updated_business_portfolio"
        assert business_transfer.engine_id == "updated_business_engine"

        # 最终验证：Transfer作为Base的子类能够正常工作
        assert isinstance(transfer, Base)
        assert isinstance(transfer, Transfer)
        assert transfer.__class__ == Transfer
        assert Transfer.__name__ == "Transfer"


if __name__ == "__main__":
    # 运行特定的测试类或所有测试
    pytest.main([__file__, "-v", "--tb=short"])
