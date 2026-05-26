"""Smoke test for FileSearchMixin -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.data.services.file_search import FileSearchMixin
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.data.services.file_search not importable")
class TestFileSearchMixinSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_mixin(self):
        """创建 Mixin 实例并注入 _crud_repo 和 _logger"""
        mixin = FileSearchMixin()
        mixin._crud_repo = MagicMock()
        mixin._logger = MagicMock()
        return mixin

    def test_instantiation(self):
        mixin = FileSearchMixin()
        assert mixin is not None

    def test_search_by_name_callable(self):
        mixin = self._make_mixin()
        mixin._crud_repo.count.return_value = 0
        mixin._crud_repo.find.return_value = []
        result = mixin.search_by_name(keyword="test")
        assert result is not None
        assert result.success

    def test_search_by_name_empty_keyword(self):
        mixin = self._make_mixin()
        result = mixin.search_by_name(keyword="")
        assert result is not None
        assert not result.success

    def test_search_by_description_callable(self):
        mixin = self._make_mixin()
        mixin._crud_repo.count.return_value = 0
        mixin._crud_repo.find.return_value = []
        result = mixin.search_by_description(keyword="test")
        assert result is not None
        assert result.success

    def test_search_callable(self):
        mixin = self._make_mixin()
        # search() uses SQLAlchemy session, mock the connection chain
        mock_conn = MagicMock()
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.count.return_value = 0
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_conn.__enter__ = MagicMock(return_value=mock_session)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mixin._crud_repo._get_connection.return_value.get_session.return_value = mock_conn
        result = mixin.search(keyword="test", search_in=["name"])
        assert result is not None
