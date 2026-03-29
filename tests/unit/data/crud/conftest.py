"""
CRUD 层 Mock 单元测试共享 fixtures

提供数据库连接、Session、CRUDResult 等通用 mock 对象
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_session():
    """模拟数据库 Session"""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.query = MagicMock()
    session.execute = MagicMock()
    session.flush = MagicMock()
    session.close = MagicMock()
    # 支持 context manager
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


@pytest.fixture
def mock_connection(mock_session):
    """模拟数据库连接对象，get_session() 返回 mock_session"""
    conn = MagicMock()
    conn.get_session.return_value = mock_session
    conn._db_type = "test"
    return conn


@pytest.fixture
def mock_glog():
    """模拟 GLOG，避免真实日志输出"""
    with patch("ginkgo.data.crud.base_crud.GLOG") as mock_log:
        mock_log.DEBUG = MagicMock()
        mock_log.INFO = MagicMock()
        mock_log.ERROR = MagicMock()
        mock_log.WARN = MagicMock()
        yield mock_log


@pytest.fixture
def mock_access_control():
    """绕过 @restrict_crud_access 装饰器"""
    with patch("ginkgo.data.access_control.service_only", lambda f: f):
        yield


@pytest.fixture
def sample_bar_params():
    """创建 Bar CRUD 的标准参数"""
    return {
        "code": "000001.SZ",
        "open": Decimal("10.50"),
        "high": Decimal("11.00"),
        "low": Decimal("10.20"),
        "close": Decimal("10.80"),
        "volume": 1000000,
        "amount": Decimal("10800000.00"),
        "timestamp": datetime(2024, 1, 1, 9, 30, 0),
    }


@pytest.fixture
def sample_stockinfo_params():
    """创建 StockInfo CRUD 的标准参数"""
    return {
        "code": "000001.SZ",
        "name": "平安银行",
    }


@pytest.fixture
def sample_order_params():
    """创建 Order CRUD 的标准参数"""
    return {
        "code": "000001.SZ",
        "direction": 1,
        "volume": 1000,
        "price": Decimal("10.50"),
    }


@pytest.fixture
def sample_position_params():
    """创建 Position CRUD 的标准参数"""
    return {
        "code": "000001.SZ",
        "volume": 1000,
        "cost": Decimal("10000.00"),
    }


@pytest.fixture
def sample_signal_params():
    """创建 Signal CRUD 的标准参数"""
    return {
        "code": "000001.SZ",
        "direction": 1,
    }
