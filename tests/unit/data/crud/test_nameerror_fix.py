"""
NameError fix 验证 — PR #4030

验证 user_crud.delete() / live_account_crud.get_live_account_by_user_id() /
       live_account_crud.get_live_account_by_uuid() / live_account_crud.get_live_accounts_by_user() /
       user_contact_crud.get_by_user() / file_crud.get_total_size_by_type()
       不再引用未定义变量。
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def patched_crud_logger():
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.GLOG", mock_logger):
        yield mock_logger


class TestUserCrudNameError:
    """user_crud.py: delete() 不再引用未定义 users"""

    @pytest.mark.unit
    def test_delete_no_nameerror(self, patched_crud_logger):
        with patch("ginkgo.data.crud.base_crud.get_db_connection"):
            from ginkgo.data.crud.user_crud import UserCRUD
            crud = UserCRUD()
            # Mock find so it doesn't need real DB
            with patch.object(crud, "find", return_value=[]):
                count = crud.delete({"uuid": "test-user"})
                assert count == 0


class TestLiveAccountCrudNameError:
    """live_account_crud.py: 三个方法不再引用未定义 results/all_accounts"""

    @pytest.mark.unit
    def test_get_live_account_by_user_id_no_nameerror(self, patched_crud_logger):
        with patch("ginkgo.data.crud.base_crud.get_db_connection"):
            from ginkgo.data.crud.live_account_crud import LiveAccountCRUD
            crud = LiveAccountCRUD()
            with patch.object(crud, "find", return_value=[]):
                accounts = crud.get_live_account_by_user_id("u-1")
                assert accounts == []

    @pytest.mark.unit
    def test_get_live_account_by_uuid_no_nameerror(self, patched_crud_logger):
        with patch("ginkgo.data.crud.base_crud.get_db_connection"):
            from ginkgo.data.crud.live_account_crud import LiveAccountCRUD
            crud = LiveAccountCRUD()
            with patch.object(crud, "find", return_value=[]):
                result = crud.get_live_account_by_uuid("uuid-1")
                assert result is None

    @pytest.mark.unit
    def test_get_live_accounts_by_user_no_nameerror(self, patched_crud_logger):
        with patch("ginkgo.data.crud.base_crud.get_db_connection"):
            from ginkgo.data.crud.live_account_crud import LiveAccountCRUD
            crud = LiveAccountCRUD()
            with patch.object(crud, "find", return_value=[]):
                result = crud.get_live_accounts_by_user(user_id="u-1")
                assert result["accounts"] == []
                assert result["total"] == 0


class TestUserContactCrudNameError:
    """user_contact_crud.py: get_by_user() 不再丢失 return"""

    @pytest.mark.unit
    def test_get_by_user_returns_list(self, patched_crud_logger):
        with patch("ginkgo.data.crud.base_crud.get_db_connection"):
            from ginkgo.data.crud.user_contact_crud import UserContactCRUD
            crud = UserContactCRUD()
            with patch.object(crud, "find", return_value=[]) as mock_find:
                result = crud.get_by_user("u-1", is_active=True)
                mock_find.assert_called_once()
                assert result == []


class TestFileCrudNameError:
    """file_crud.py: get_total_size_by_type() 不再引用未定义 files"""

    @pytest.mark.unit
    def test_get_total_size_by_type_no_nameerror(self, patched_crud_logger):
        with patch("ginkgo.data.crud.base_crud.get_db_connection"):
            from ginkgo.data.crud.file_crud import FileCRUD
            crud = FileCRUD()
            with patch.object(crud, "find", return_value=[]) as mock_find:
                total = crud.get_total_size_by_type("csv")
                mock_find.assert_called_once_with(filters={"file_type": "csv"})
                assert total == 0
