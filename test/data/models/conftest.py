"""
数据模型测试共享fixtures

提供跨测试文件共享的pytest fixtures
"""
import pytest
import datetime
import uuid
from decimal import Decimal
from unittest.mock import Mock, MagicMock
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


@pytest.fixture
def sample_uuid():
    """生成示例UUID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_timestamp():
    """生成示例时间戳"""
    return datetime.datetime(2024, 1, 1, 12, 0, 0)


@pytest.fixture
def sample_engine_id():
    """生成示例引擎ID"""
    return "test_engine_001"


@pytest.fixture
def sample_run_id():
    """生成示例运行ID"""
    return "test_run_20240101_120000"


@pytest.fixture
def ginkgo_config():
    """Ginkgo配置fixture"""
    try:
        from ginkgo.libs import GCONF
        GCONF.set_debug(True)
        yield GCONF
        GCONF.set_debug(False)
    except ImportError:
        yield None


@pytest.fixture
def mock_base_model():
    """模拟MBase模型"""
    mock = Mock()
    mock.uuid = str(uuid.uuid4())
    mock.timestamp = datetime.datetime.now()
    mock.meta = "{}"
    mock.desc = "Test model"
    mock.source = -1
    return mock


@pytest.fixture
def sample_price_data():
    """示例价格数据"""
    return {
        "open": Decimal("10.50"),
        "high": Decimal("11.00"),
        "low": Decimal("10.20"),
        "close": Decimal("10.80"),
        "volume": 1000000,
        "amount": Decimal("10800000.00")
    }


@pytest.fixture
def sample_position_data():
    """示例持仓数据"""
    return {
        "portfolio_id": str(uuid.uuid4()),
        "code": "000001.SZ",
        "cost": Decimal("10000.00"),
        "volume": 1000,
        "frozen_volume": 0,
        "price": Decimal("10.50"),
        "fee": Decimal("5.00")
    }


@pytest.fixture
def sample_bar_data():
    """示例K线数据"""
    return {
        "code": "000001.SZ",
        "timestamp": datetime.datetime(2024, 1, 1, 9, 30, 0),
        "open": Decimal("10.50"),
        "high": Decimal("11.00"),
        "low": Decimal("10.20"),
        "close": Decimal("10.80"),
        "volume": 1000000,
        "amount": Decimal("10800000.00"),
        "frequency": 1  # DAY
    }


@pytest.fixture
def sample_tick_data():
    """示例Tick数据"""
    return {
        "code": "000001.SZ",
        "timestamp": datetime.datetime(2024, 1, 1, 9, 30, 0, 500000),
        "price": Decimal("10.50"),
        "volume": 1000,
        "amount": Decimal("10500.00"),
        "direction": 1  # BUY
    }


@pytest.fixture
def sample_order_data():
    """示例订单数据"""
    return {
        "portfolio_id": str(uuid.uuid4()),
        "code": "000001.SZ",
        "direction": 1,  # LONG
        "price": Decimal("10.50"),
        "volume": 1000,
        "type": 1  # LIMIT
    }


@pytest.fixture
def sample_signal_data():
    """示例信号数据"""
    return {
        "portfolio_id": str(uuid.uuid4()),
        "code": "000001.SZ",
        "direction": 1,  # LONG
        "strength": Decimal("0.8")
    }


@pytest.fixture
def mock_database_session():
    """模拟数据库会话"""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.query = MagicMock()
    session.execute = MagicMock()
    return session


@pytest.fixture
def mock_database_engine():
    """模拟数据库引擎"""
    engine = MagicMock()
    engine.connect = MagicMock()
    engine.raw_connection = MagicMock()
    return engine


@pytest.fixture
def mock_driver():
    """模拟数据库驱动"""
    driver = MagicMock()
    driver.driver_name = "test_driver"
    driver._db_type = "test"
    driver._engine = None
    driver._session_factory = None
    driver._streaming_engine = None
    driver._streaming_session_factory = None
    driver._streaming_enabled = False
    return driver


@pytest.fixture
def mock_logger():
    """模拟日志器"""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


# 参数化测试数据
@pytest.fixture
def invalid_prices():
    """无效价格数据"""
    return [
        (Decimal("-1.00"), "negative price"),
        (Decimal("0"), "zero price"),
        (None, "null price"),
        ("invalid", "string price")
    ]


@pytest.fixture
def invalid_volumes():
    """无效成交量数据"""
    return [
        (-1, "negative volume"),
        (0, "zero volume"),
        (None, "null volume"),
        ("invalid", "string volume")
    ]


@pytest.fixture
def boundary_values():
    """边界值测试数据"""
    return {
        "max_volume": 2**31 - 1,  # 最大32位整数
        "min_volume": 1,
        "max_price": Decimal("999999.99"),
        "min_price": Decimal("0.01"),
        "max_code_length": 32
    }
