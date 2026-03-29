"""
CRUD测试共用的Pytest Fixtures

提供所有CRUD测试共享的fixtures：
- db_cleanup: 测试数据清理
- crud_test_config: 测试配置
- sample_data: 各类CRUD的测试数据
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.enums import (
    SOURCE_TYPES, MARKET_TYPES, FILE_TYPES,
    PORTFOLIO_MODE_TYPES, PORTFOLIO_RUNSTATE_TYPES,
    TRANSFERDIRECTION_TYPES, TRANSFERSTATUS_TYPES
)


@pytest.fixture(scope="function")
def db_cleanup():
    """
    数据库清理fixture
    在测试后自动清理测试数据

    使用方式:
        @pytest.mark.db_cleanup
        def test_something(db_cleanup):
            # 测试代码
            pass

    注意: 需要CRUD类配置CRUD_TEST_CONFIG
    """
    cleanup_filters = {}
    yield cleanup_filters

    # 如果测试类有CRUD_TEST_CONFIG，执行清理
    # 这里可以添加自动清理逻辑


@pytest.fixture(scope="function")
def ginkgo_config():
    """
    Ginkgo配置fixture
    设置调试模式用于数据库操作
    """
    from ginkgo.libs import GCONF
    GCONF.set_debug(True)
    yield GCONF
    # GCONF.set_debug(False)  # 可选：测试后关闭调试模式


@pytest.fixture(scope="session")
def sample_portfolio_data():
    """Portfolio测试数据fixture"""
    return [
        {
            "name": "test_portfolio_ma_strategy",
            "mode": PORTFOLIO_MODE_TYPES.BACKTEST.value,
            "state": PORTFOLIO_RUNSTATE_TYPES.INITIALIZED.value,
            "source": SOURCE_TYPES.TEST
        },
        {
            "name": "test_portfolio_rsi_strategy",
            "mode": PORTFOLIO_MODE_TYPES.LIVE.value,
            "state": PORTFOLIO_RUNSTATE_TYPES.RUNNING.value,
            "source": SOURCE_TYPES.TEST
        }
    ]


@pytest.fixture(scope="session")
def sample_trade_day_data():
    """TradeDay测试数据fixture"""
    base_date = datetime(2023, 1, 1)
    return [
        {
            "market": MARKET_TYPES.CHINA,
            "is_open": (base_date + timedelta(days=i)).weekday() < 5,
            "timestamp": base_date + timedelta(days=i),
            "source": SOURCE_TYPES.TEST
        }
        for i in range(10)
    ]


@pytest.fixture(scope="session")
def sample_file_data():
    """File测试数据fixture"""
    return [
        {
            "name": "strategy_config.ini",
            "type": FILE_TYPES.STRATEGY,
            "data": b"[strategy]\nname = ma_cross\nshort = 5\nlong = 20",
            "source": SOURCE_TYPES.TEST
        },
        {
            "name": "stock_data.csv",
            "type": FILE_TYPES.INDEX,
            "data": b"2023-01-01,000001.SZ,10.50,1000",
            "source": SOURCE_TYPES.TEST
        }
    ]


@pytest.fixture(scope="session")
def sample_transfer_data():
    """Transfer测试数据fixture"""
    base_time = datetime(2023, 1, 3, 9, 30)
    return [
        {
            "portfolio_id": "test_portfolio_001",
            "engine_id": "test_engine_001",
            "run_id": "test_run_001",
            "direction": TRANSFERDIRECTION_TYPES.IN,
            "market": MARKET_TYPES.CHINA,
            "money": Decimal("100000.00"),
            "status": TRANSFERSTATUS_TYPES.FILLED,
            "source": SOURCE_TYPES.TEST,
            "timestamp": base_time
        },
        {
            "portfolio_id": "test_portfolio_001",
            "engine_id": "test_engine_001",
            "run_id": "test_run_001",
            "direction": TRANSFERDIRECTION_TYPES.OUT,
            "market": MARKET_TYPES.CHINA,
            "money": Decimal("5000.00"),
            "status": TRANSFERSTATUS_TYPES.FILLED,
            "source": SOURCE_TYPES.TEST,
            "timestamp": base_time + timedelta(hours=1)
        }
    ]


@pytest.fixture(scope="function")
def verify_insert_count():
    """
    验证插入数量的fixture
    参数化不同的插入场景

    使用示例:
        @pytest.mark.parametrize("insert_count", [1, 5, 10])
        def test_batch_insert(verify_insert_count, insert_count):
            # 测试代码
            pass
    """
    def _verify(before_count, after_count, expected_count):
        actual = after_count - before_count
        assert actual == expected_count, f"插入数量验证失败：预期增加{expected_count}条，实际增加{actual}条"
        return actual

    return _verify


@pytest.fixture(scope="function")
def print_test_header():
    """
    打印测试头部的fixture
    标准化测试输出格式

    使用示例:
        def test_something(print_test_header):
            print_test_header("测试名称", "测试描述")
            # 测试代码
    """
    def _print_header(test_name, description=""):
        print("\n" + "="*60)
        print(f"开始测试: {test_name}")
        if description:
            print(f"测试描述: {description}")
        print("="*60)

    return _print_header


@pytest.fixture(scope="function")
def assert_data_integrity():
    """
    数据完整性断言fixture
    提供常用的数据完整性检查

    使用示例:
        def test_data_integrity(assert_data_integrity, data):
            assert_data_integrity.check_uuid(data.uuid)
            assert_data_integrity.check_timestamp(data.timestamp)
    """
    class IntegrityChecker:
        @staticmethod
        def check_uuid(uuid_value, msg="UUID验证"):
            assert uuid_value is not None, f"{msg}: UUID不应为空"
            assert len(str(uuid_value)) > 0, f"{msg}: UUID不应为空字符串"
            return True

        @staticmethod
        def check_timestamp(timestamp_value, msg="时间戳验证"):
            assert timestamp_value is not None, f"{msg}: 时间戳不应为空"
            assert isinstance(timestamp_value, datetime), f"{msg}: 时间戳应为datetime类型"
            return True

        @staticmethod
        def check_enum_value(value, enum_type, msg="枚举值验证"):
            valid_values = [e.value for e in enum_type]
            assert value in valid_values, f"{msg}: 值{value}不在有效枚举值{valid_values}中"
            return True

        @staticmethod
        def check_string_field(field_value, max_length=None, msg="字符串字段验证"):
            assert field_value is not None, f"{msg}: 字段不应为空"
            assert len(str(field_value).strip()) > 0, f"{msg}: 字段不应为空字符串"
            if max_length:
                assert len(field_value) <= max_length, f"{msg}: 字段长度{len(field_value)}超过限制{max_length}"
            return True

    return IntegrityChecker


@pytest.fixture(scope="function")
def measure_performance():
    """
    性能测量fixture
    用于测量操作执行时间

    使用示例:
        def test_query_performance(measure_performance):
            with measure_performance("查询操作"):
                # 执行查询
                result = crud.find()
    """
    import time
    import contextlib

    @contextlib.contextmanager
    def _measure(operation_name):
        start_time = time.time()
        yield
        elapsed = time.time() - start_time
        print(f"✓ {operation_name} 耗时: {elapsed:.4f}秒")

        # 性能阈值警告（可根据需要调整）
        if elapsed > 5.0:
            print(f"⚠ 警告: {operation_name} 耗时过长 ({elapsed:.4f}秒)")

    return _measure


# Pytest标记配置
def pytest_configure(config):
    """注册自定义pytest标记"""
    config.addinivalue_line(
        "markers", "database: 标记需要数据库连接的测试"
    )
    config.addinivalue_line(
        "markers", "tdd: 标记TDD测试用例"
    )
    config.addinivalue_line(
        "markers", "db_cleanup: 标记需要清理测试数据的测试"
    )
    config.addinivalue_line(
        "markers", "enum: 标记枚举类型测试"
    )
    config.addinivalue_line(
        "markers", "financial: 标记金融计算测试"
    )
    config.addinivalue_line(
        "markers", "slow: 标记运行缓慢的测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记集成测试"
    )
    config.addinivalue_line(
        "markers", "unit: 标记单元测试"
    )
