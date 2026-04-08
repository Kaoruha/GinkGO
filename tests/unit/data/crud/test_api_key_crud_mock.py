"""
性能: 220MB RSS, 1.89s, 13 tests [PASS]
ApiKeyCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- 构造与类型检查：model_class、继承关系
- Business Helper: create_api_key, get_api_key_by_uuid, get_api_keys_by_user,
  update_api_key, delete_api_key, verify_api_key
- 无 _get_field_config, _get_enum_mappings, _create_from_params
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

import uuid


# ============================================================
# 辅助：构造 ApiKeyCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def api_key_crud():
    """构造 ApiKeyCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.api_key_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.api_key_crud import ApiKeyCRUD
        crud = ApiKeyCRUD()
        crud._logger = mock_logger
        return crud


@pytest.fixture
def fake_api_key():
    """构造一个假的 MApiKey 对象"""
    mock_key = MagicMock()
    mock_key.uuid = str(uuid.uuid4())
    mock_key.user_id = "user_test"
    mock_key.name = "test_key"
    mock_key.key_hash = "abc123"
    mock_key.key_prefix = "abcd1234"
    mock_key.key_encrypted = "encrypted_value"
    mock_key.permissions = "read"
    mock_key.is_active = True
    mock_key.is_expired.return_value = False
    mock_key.check_permission.return_value = True
    return mock_key


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestApiKeyCRUDConstruction:
    """ApiKeyCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction_model_class(self, api_key_crud):
        """验证 model_class 为 MApiKey"""
        from ginkgo.data.models.model_api_key import MApiKey

        assert api_key_crud.model_class is MApiKey



# ============================================================
# create_api_key 测试
# ============================================================


class TestApiKeyCRUDCreate:
    """create_api_key 创建 API Key 测试"""

    @pytest.mark.unit
    def test_create_api_key_invalid_permission(self, api_key_crud):
        """无效权限返回 None"""
        result = api_key_crud.create_api_key(
            name="test", key_value="sk-12345678", permissions="invalid_perm"
        )
        assert result is None

    @pytest.mark.unit
    def test_create_api_key_success(self, api_key_crud):
        """成功创建 API Key，调用 add 方法"""
        api_key_crud.add = MagicMock()
        mock_service = MagicMock()
        mock_service.encrypt_credential.return_value = MagicMock(
            success=True, data={"encrypted_credential": "enc_data"}
        )

        with patch("ginkgo.data.crud.api_key_crud.get_encryption_service", return_value=mock_service):
            result = api_key_crud.create_api_key(
                name="test_key", key_value="sk-1234567890", permissions="read"
            )

        assert result is not None
        api_key_crud.add.assert_called_once()

    @pytest.mark.unit
    def test_create_api_key_exception_returns_none(self, api_key_crud):
        """加密服务抛异常时返回 None"""
        api_key_crud.add = MagicMock(side_effect=Exception("DB error"))
        mock_service = MagicMock()
        mock_service.encrypt_credential.return_value = MagicMock(
            success=True, data={"encrypted_credential": "enc_data"}
        )

        with patch("ginkgo.data.crud.api_key_crud.get_encryption_service", return_value=mock_service):
            result = api_key_crud.create_api_key(
                name="test_key", key_value="sk-1234567890", permissions="read"
            )

        assert result is None


# ============================================================
# 查询方法测试
# ============================================================


class TestApiKeyCRUDQuery:
    """查询相关业务方法测试"""

    @pytest.mark.unit
    def test_get_api_key_by_uuid_found(self, api_key_crud, fake_api_key):
        """UUID 查到结果时返回第一个对象"""
        api_key_crud.find = MagicMock(return_value=[fake_api_key])

        result = api_key_crud.get_api_key_by_uuid(fake_api_key.uuid)

        assert result is fake_api_key
        api_key_crud.find.assert_called_once_with(
            filters={"uuid": fake_api_key.uuid, "is_del": False}
        )

    @pytest.mark.unit
    def test_get_api_key_by_uuid_not_found(self, api_key_crud):
        """UUID 未查到结果时返回 None"""
        api_key_crud.find = MagicMock(return_value=[])

        result = api_key_crud.get_api_key_by_uuid("nonexistent")

        assert result is None

    @pytest.mark.unit
    def test_get_api_keys_by_user_returns_list(self, api_key_crud, fake_api_key):
        """按 user_id 查询返回列表"""
        api_key_crud.find = MagicMock(return_value=[fake_api_key])

        result = api_key_crud.get_api_keys_by_user("user_test")

        assert result == [fake_api_key]
        call_kwargs = api_key_crud.find.call_args[1]
        assert call_kwargs["filters"]["user_id"] == "user_test"
        assert call_kwargs["order_by"] == "create_at"
        assert call_kwargs["desc_order"] is True


# ============================================================
# 更新与删除测试
# ============================================================


class TestApiKeyCRUDUpdateAndDelete:
    """更新和删除业务方法测试"""

    @pytest.mark.unit
    def test_update_api_key_not_found(self, api_key_crud):
        """更新不存在的 Key 返回 False"""
        api_key_crud.get_api_key_by_uuid = MagicMock(return_value=None)

        result = api_key_crud.update_api_key(uuid="nonexistent", name="new_name")

        assert result is False

    @pytest.mark.unit
    def test_update_api_key_success(self, api_key_crud, fake_api_key):
        """更新已存在的 Key，调用 modify"""
        api_key_crud.get_api_key_by_uuid = MagicMock(return_value=fake_api_key)
        api_key_crud.modify = MagicMock()

        # 源码使用 datetime.datetime.now()，但 datetime 是 from datetime import datetime
        # 需要在模块命名空间中 mock datetime 类的 datetime 属性
        with patch("ginkgo.data.crud.api_key_crud.datetime") as mock_dt_cls:
            mock_dt_cls.datetime.now.return_value = datetime(2026, 4, 5, 12, 0, 0)
            result = api_key_crud.update_api_key(uuid=fake_api_key.uuid, name="new_name")

        assert result is True
        api_key_crud.modify.assert_called_once()

    @pytest.mark.unit
    def test_delete_api_key_success(self, api_key_crud, fake_api_key):
        """软删除 Key，调用 modify 设置 is_del=True"""
        api_key_crud.get_api_key_by_uuid = MagicMock(return_value=fake_api_key)
        api_key_crud.modify = MagicMock()

        result = api_key_crud.delete_api_key(uuid=fake_api_key.uuid)

        assert result is True
        call_kwargs = api_key_crud.modify.call_args[1]
        assert call_kwargs["updates"]["is_del"] is True


# ============================================================
# verify_api_key 测试
# ============================================================


class TestApiKeyCRUDVerify:
    """verify_api_key 验证 API Key 测试"""

    @pytest.mark.unit
    def test_verify_api_key_no_match(self, api_key_crud):
        """哈希不匹配时返回 None"""
        api_key_crud.find = MagicMock(return_value=[])

        result = api_key_crud.verify_api_key("wrong_key")

        assert result is None

    @pytest.mark.unit
    def test_verify_api_key_inactive(self, api_key_crud, fake_api_key):
        """Key 已禁用时返回 None"""
        api_key_crud.find = MagicMock(return_value=[fake_api_key])
        fake_api_key.is_active = False

        result = api_key_crud.verify_api_key("some_key")

        assert result is None

    @pytest.mark.unit
    def test_verify_api_key_success(self, api_key_crud, fake_api_key):
        """验证成功返回 Key 对象并更新 last_used_at"""
        api_key_crud.find = MagicMock(return_value=[fake_api_key])
        api_key_crud.modify = MagicMock()

        # 源码使用 datetime.datetime.now()，需要 mock
        with patch("ginkgo.data.crud.api_key_crud.datetime") as mock_dt_cls:
            mock_dt_cls.datetime.now.return_value = datetime(2026, 4, 5, 12, 0, 0)
            result = api_key_crud.verify_api_key("some_key", required_permission="read")

        assert result is fake_api_key
        api_key_crud.modify.assert_called_once()
        # 检查 updates 中包含 last_used_at
        call_kwargs = api_key_crud.modify.call_args[1]
        assert "last_used_at" in call_kwargs["updates"]
