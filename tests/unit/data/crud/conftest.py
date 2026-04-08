"""
CRUD 层 Mock 单元测试共享 fixtures

提供数据库连接、Session、CRUDResult 等通用 mock 对象
"""
import pytest
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
