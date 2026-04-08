"""
性能: 218MB RSS, 1.88s, 5 tests [PASS]
NotificationRecipientCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- Business Helper: get_by_name, get_active_recipients
- 构造与类型检查

注意：NotificationRecipientCRUD 无 field_config、enum_mappings、create_from_params，仅测试构造和业务方法。
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import RECIPIENT_TYPES


# ============================================================
# 辅助：构造 NotificationRecipientCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def crud_instance():
    """构造 NotificationRecipientCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.notification_recipient_crud.GLOG", mock_logger):
        from ginkgo.data.crud.notification_recipient_crud import NotificationRecipientCRUD
        crud = NotificationRecipientCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestNotificationRecipientCRUDConstruction:
    """NotificationRecipientCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, crud_instance):
        """验证 model_class 为 MNotificationRecipient，_is_mysql 为 True"""
        from ginkgo.data.models.model_notification_recipient import MNotificationRecipient

        assert crud_instance.model_class is MNotificationRecipient
        assert crud_instance._is_mysql is True
        assert crud_instance._is_clickhouse is False



# ============================================================
# Business Helper 测试
# ============================================================


class TestNotificationRecipientCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_get_by_name_found(self, crud_instance):
        """get_by_name 找到接收人时返回对象"""
        mock_recipient = MagicMock()
        crud_instance.find = MagicMock(return_value=[mock_recipient])

        result = crud_instance.get_by_name(name="admin")

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["name"] == "admin"
        assert call_kwargs["filters"]["is_del"] is False
        assert call_kwargs["page_size"] == 1
        assert result is mock_recipient

    @pytest.mark.unit
    def test_get_by_name_not_found(self, crud_instance):
        """get_by_name 未找到接收人时返回 None"""
        crud_instance.find = MagicMock(return_value=[])

        result = crud_instance.get_by_name(name="nonexistent")

        assert result is None

    @pytest.mark.unit
    def test_get_active_recipients(self, crud_instance):
        """get_active_recipients 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        result = crud_instance.get_active_recipients()

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["is_del"] is False
        assert result == []

    @pytest.mark.unit
    def test_get_active_recipients_with_type(self, crud_instance):
        """get_active_recipients 传入 recipient_type 过滤"""
        crud_instance.find = MagicMock(return_value=[])

        crud_instance.get_active_recipients(recipient_type=RECIPIENT_TYPES.USER)

        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["recipient_type"] == RECIPIENT_TYPES.USER.value
