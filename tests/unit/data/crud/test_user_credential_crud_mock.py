"""
UserCredentialCRUD 单元测试（Mock 数据库连接）

#3897: 验证 get_by_user_id 使用 ModelList.first() 而非 results[0]
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.data.crud.model_conversion import ModelList


@pytest.fixture
def crud_instance():
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.user_credential_crud import UserCredentialCRUD
        crud = UserCredentialCRUD()
        crud._logger = mock_logger
        return crud


class TestGetByUserIdReturnsFirst:
    """#3897: get_by_user_id 应使用 ModelList.first() 语义"""

    @pytest.mark.unit
    def test_returns_none_when_empty(self, crud_instance):
        """空结果应返回 None"""
        crud_instance.find = MagicMock(return_value=ModelList([], crud_instance))
        assert crud_instance.get_by_user_id("user-1") is None

    @pytest.mark.unit
    def test_returns_first_match(self, crud_instance):
        """有结果时返回第一条"""
        mock_model = MagicMock()
        crud_instance.find = MagicMock(return_value=ModelList([mock_model], crud_instance))
        assert crud_instance.get_by_user_id("user-1") is mock_model

    @pytest.mark.unit
    def test_returns_first_of_multiple(self, crud_instance):
        """多条结果只返回第一条"""
        first, second = MagicMock(), MagicMock()
        crud_instance.find = MagicMock(return_value=ModelList([first, second], crud_instance))
        assert crud_instance.get_by_user_id("user-1") is first
