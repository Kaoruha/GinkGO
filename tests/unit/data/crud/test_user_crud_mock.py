"""
性能: 220MB RSS, 2.0s, 10 tests [PASS]
UserCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置（user_type, username, is_active）
- _get_enum_mappings: 枚举映射（USER_TYPES, SOURCE_TYPES）
- _create_from_params: 参数转 MUser 模型
- Business Helper: find_active_users, fuzzy_search
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES, USER_TYPES


# ============================================================
# 辅助：构造 UserCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def crud_instance():
    """构造 UserCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.user_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.user_crud import UserCRUD
        crud = UserCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestUserCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, crud_instance):
        """配置包含 user_type, username, is_active"""
        config = crud_instance._get_field_config()

        required_keys = {"user_type", "username", "is_active"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_user_type_is_enum(self, crud_instance):
        """user_type 字段为枚举类型"""
        config = crud_instance._get_field_config()

        assert config["user_type"]["type"] == "enum"

    @pytest.mark.unit
    def test_field_config_username_validation(self, crud_instance):
        """username 字段为 string 类型，max=64"""
        config = crud_instance._get_field_config()

        assert config["username"]["type"] == "string"
        assert config["username"]["max"] == 64


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestUserCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_two_enums(self, crud_instance):
        """映射包含 user_type 和 source 两个枚举"""
        mappings = crud_instance._get_enum_mappings()

        assert "user_type" in mappings
        assert "source" in mappings
        assert mappings["user_type"] is USER_TYPES
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestUserCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, crud_instance):
        """传入完整参数，返回 MUser 模型且属性正确"""
        from ginkgo.data.models import MUser

        params = {
            "username": "测试用户",
            "user_type": USER_TYPES.PERSON,
        }

        model = crud_instance._create_from_params(**params)

        assert isinstance(model, MUser)
        assert model.username == "测试用户"
        assert model.is_active is True

    @pytest.mark.unit
    def test_create_from_params_defaults(self, crud_instance):
        """缺失字段使用默认值"""
        model = crud_instance._create_from_params()

        assert model.is_active is True


# ============================================================
# Business Helper 测试
# ============================================================


class TestUserCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_active_users(self, crud_instance):
        """find_active_users 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        crud_instance.find_active_users()

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["is_active"] is True

    @pytest.mark.unit
    def test_fuzzy_search_uuid_pattern(self, crud_instance):
        """fuzzy_search 检测 UUID 格式时调用 _get_connection 进行精确匹配"""
        # fuzzy_search 内部使用 _get_connection，mock 掉
        mock_conn = MagicMock()
        mock_session = MagicMock()
        mock_conn.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_conn.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.all.return_value = []
        crud_instance._get_connection = MagicMock(return_value=mock_conn)

        crud_instance.fuzzy_search("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4")

        crud_instance._get_connection.assert_called_once()
        mock_session.query.assert_called_once()

    @pytest.mark.unit
    def test_fuzzy_search_limit_pushes_sql_limit(self, crud_instance):
        """#6572: fuzzy_search 传 limit 时下推到 SQL LIMIT（非全量拉回）"""
        mock_conn = MagicMock()
        mock_session = MagicMock()
        mock_conn.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_conn.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        crud_instance._get_connection = MagicMock(return_value=mock_conn)

        crud_instance.fuzzy_search("Alice", limit=5)

        mock_session.query.return_value.filter.return_value.limit.assert_called_once_with(5)

    @pytest.mark.unit
    def test_fuzzy_search_no_limit_keeps_full_query(self, crud_instance):
        """#6572: limit=None 保持全量返回（零破坏现有调用方）"""
        mock_conn = MagicMock()
        mock_session = MagicMock()
        mock_conn.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_conn.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.filter.return_value.all.return_value = []
        crud_instance._get_connection = MagicMock(return_value=mock_conn)

        crud_instance.fuzzy_search("Alice")

        # limit 未传时不应在 query 链上调用 .limit()
        mock_session.query.return_value.filter.return_value.limit.assert_not_called()


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestUserCRUDCascadeCredentials:
    """级联软删除凭据测试 — #3896"""

    @pytest.mark.unit
    def test_cascade_delete_credentials_method_exists(self, crud_instance):
        """UserCRUD 拥有 _cascade_delete_credentials 方法"""
        assert hasattr(crud_instance, "_cascade_delete_credentials")

    @pytest.mark.unit
    def test_delete_calls_cascade_delete_credentials(self, crud_instance):
        """delete() 应调用 _cascade_delete_credentials"""
        crud_instance._cascade_delete_credentials = MagicMock(return_value=0)
        crud_instance._cascade_delete_group_mappings = MagicMock(return_value=0)
        crud_instance._cascade_delete_contacts = MagicMock(return_value=0)

        mock_user = MagicMock()
        mock_user.uuid = "test-uuid-123"
        crud_instance.find = MagicMock(return_value=[mock_user])

        mock_conn = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_conn.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_conn.get_session.return_value.__exit__ = MagicMock(return_value=False)
        crud_instance._get_connection = MagicMock(return_value=mock_conn)

        crud_instance.delete(filters={"uuid": "test-uuid-123"})

        crud_instance._cascade_delete_credentials.assert_called_once_with(
            ["test-uuid-123"], session=mock_session
        )


class TestUserCRUDConstruction:
    """UserCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, crud_instance):
        """验证 model_class 为 MUser，_is_mysql 为 True"""
        from ginkgo.data.models import MUser

        assert crud_instance.model_class is MUser
        assert crud_instance._is_mysql is True
        assert crud_instance._is_clickhouse is False


class TestUserCRUDTransactions:
    """事务边界回归测试"""

    @pytest.mark.unit
    def test_delete_reuses_single_transaction_session_for_all_cascade_steps(self, crud_instance):
        transaction_session = MagicMock()
        transaction_session.execute.return_value.rowcount = 1
        seen_sessions = []

        from contextlib import contextmanager

        @contextmanager
        def fake_scope(session=None):
            assert session is None
            yield transaction_session

        mock_user = MagicMock()
        mock_user.uuid = "user-1"

        def fake_find(*args, **kwargs):
            seen_sessions.append(("find", kwargs.get("session")))
            return [mock_user]

        def fake_group(*args, **kwargs):
            seen_sessions.append(("group", kwargs.get("session")))
            return 1

        def fake_contacts(*args, **kwargs):
            seen_sessions.append(("contacts", kwargs.get("session")))
            return 1

        def fake_credentials(*args, **kwargs):
            seen_sessions.append(("credentials", kwargs.get("session")))
            return 1

        crud_instance._session_scope = fake_scope
        crud_instance.find = fake_find
        crud_instance._cascade_delete_group_mappings = fake_group
        crud_instance._cascade_delete_contacts = fake_contacts
        crud_instance._cascade_delete_credentials = fake_credentials

        result = crud_instance.delete(filters={"uuid": "user-1"})

        assert result == 1
        assert seen_sessions == [
            ("find", transaction_session),
            ("group", transaction_session),
            ("contacts", transaction_session),
            ("credentials", transaction_session),
        ]
        transaction_session.commit.assert_not_called()
        transaction_session.close.assert_not_called()

    @pytest.mark.unit
    def test_cascade_delete_credentials_with_external_session_does_not_commit(self, crud_instance):
        session = MagicMock()
        session.execute.return_value.rowcount = 2

        result = crud_instance._cascade_delete_credentials(["user-1"], session=session)

        assert result == 2
        session.execute.assert_called_once()
        session.commit.assert_not_called()
        session.close.assert_not_called()
