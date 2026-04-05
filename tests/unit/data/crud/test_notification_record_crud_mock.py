# Upstream: BaseMongoCRUD (继承)、MNotificationRecord (模型)
# Downstream: None (单元测试)
# Role: NotificationRecordCRUD 通知记录 CRUD 单元测试（Mock MongoDB 驱动）


"""
NotificationRecordCRUD 单元测试（Mock MongoDB 驱动）

覆盖范围：
- 构造与类型检查：model_class、driver 绑定
- add：添加记录成功/失败
- get_by_message_id：按消息ID查询，验证查询条件
- get_by_user：按用户UUID查询，验证排序/过滤
- get_by_status / get_recent_failed：按状态查询
- update_status：更新状态，验证 $set 字段
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


# ============================================================
# 辅助：构造 NotificationRecordCRUD 实例（mock MongoDB 驱动）
# ============================================================


@pytest.fixture
def mock_driver():
    """mock GinkgoMongo 驱动"""
    driver = MagicMock()
    driver.get_collection.return_value = MagicMock()
    return driver


@pytest.fixture
def crud(mock_driver):
    """构造 NotificationRecordCRUD 实例，注入 mock 驱动"""
    with patch("ginkgo.data.crud.base_mongo_crud.GLOG", MagicMock()), \
         patch("ginkgo.data.crud.notification_record_crud.GLOG", MagicMock()), \
         patch("ginkgo.data.crud.base_mongo_crud.ModelCRUDMapping.register"):
        from ginkgo.data.crud.notification_record_crud import NotificationRecordCRUD
        from ginkgo.data.models.model_notification_record import MNotificationRecord
        return NotificationRecordCRUD(
            model_class=MNotificationRecord,
            driver=mock_driver,
        )


@pytest.fixture
def fake_record():
    """构造假的 MNotificationRecord"""
    from ginkgo.data.models.model_notification_record import MNotificationRecord
    record = MagicMock(spec=MNotificationRecord)
    record.uuid = "fake_uuid_001"
    record.message_id = "msg_001"
    record.model_dump_for_mongo.return_value = {"uuid": "fake_uuid_001", "message_id": "msg_001"}
    return record


# ============================================================
# 构造与类型检查
# ============================================================


class TestNotificationRecordCRUDConstruction:
    """NotificationRecordCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_model_class_is_correct(self, crud):
        """验证 model_class 为 MNotificationRecord"""
        from ginkgo.data.models.model_notification_record import MNotificationRecord
        assert crud.model_class is MNotificationRecord

    @pytest.mark.unit
    def test_driver_is_bound(self, crud, mock_driver):
        """验证 driver 正确绑定"""
        assert crud._driver is mock_driver

    @pytest.mark.unit
    def test_get_collection_delegates_to_driver(self, crud, mock_driver):
        """_get_collection 调用 driver.get_collection"""
        crud._get_collection()
        mock_driver.get_collection.assert_called_once()

    @pytest.mark.unit
    def test_class_level_model_class(self):
        """类属性 _model_class 正确设置"""
        with patch("ginkgo.data.crud.base_mongo_crud.GLOG", MagicMock()), \
             patch("ginkgo.data.crud.base_mongo_crud.ModelCRUDMapping.register"):
            from ginkgo.data.crud.notification_record_crud import NotificationRecordCRUD
            from ginkgo.data.models.model_notification_record import MNotificationRecord
            assert NotificationRecordCRUD._model_class is MNotificationRecord


# ============================================================
# add 添加记录
# ============================================================


class TestNotificationRecordCRUDAdd:
    """add 添加通知记录测试"""

    @pytest.mark.unit
    def test_add_success(self, crud, fake_record):
        """添加成功返回 UUID"""
        mock_collection = crud._driver.get_collection.return_value
        mock_result = MagicMock()
        mock_result.inserted_id = "some_object_id"
        mock_collection.insert_one.return_value = mock_result

        result = crud.add(fake_record)

        assert result == "fake_uuid_001"
        fake_record.model_dump_for_mongo.assert_called_once()
        mock_collection.insert_one.assert_called_once()

    @pytest.mark.unit
    def test_add_failure_returns_none(self, crud, fake_record):
        """添加失败（异常）返回 None"""
        mock_collection = crud._driver.get_collection.return_value
        mock_collection.insert_one.side_effect = Exception("DB error")

        result = crud.add(fake_record)

        assert result is None


# ============================================================
# get_by_message_id 按消息ID查询
# ============================================================


class TestNotificationRecordCRUDGetByMessageId:
    """get_by_message_id 按消息ID查询测试"""

    @pytest.mark.unit
    def test_query_with_correct_filter(self, crud):
        """验证查询条件包含 message_id 和 is_del=False"""
        mock_collection = crud._driver.get_collection.return_value
        mock_collection.find_one.return_value = None

        crud.get_by_message_id("msg_001")

        mock_collection.find_one.assert_called_once()
        call_args = mock_collection.find_one.call_args[0][0]
        assert call_args["message_id"] == "msg_001"
        assert call_args["is_del"] is False

    @pytest.mark.unit
    def test_returns_none_when_not_found(self, crud):
        """未找到记录返回 None"""
        mock_collection = crud._driver.get_collection.return_value
        mock_collection.find_one.return_value = None

        result = crud.get_by_message_id("nonexistent")

        assert result is None

    @pytest.mark.unit
    def test_returns_model_when_found(self, crud):
        """找到记录时调用 _doc_to_model"""
        mock_collection = crud._driver.get_collection.return_value
        fake_doc = {"uuid": "abc", "message_id": "msg_001", "is_del": False}
        mock_collection.find_one.return_value = fake_doc

        with patch.object(crud, "_doc_to_model") as mock_convert:
            mock_convert.return_value = "converted_model"
            result = crud.get_by_message_id("msg_001")
            assert result == "converted_model"


# ============================================================
# get_by_user / get_by_status / get_recent_failed
# ============================================================


class TestNotificationRecordCRUDQueries:
    """按用户/状态查询测试"""

    @pytest.mark.unit
    def test_get_by_user_query_filter(self, crud):
        """验证 get_by_user 查询条件包含 user_uuid 和 is_del"""
        mock_collection = crud._driver.get_collection.return_value
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = []
        mock_collection.find.return_value = mock_cursor

        crud.get_by_user("user_123", limit=50)

        call_args = mock_collection.find.call_args[0][0]
        assert call_args["user_uuid"] == "user_123"
        assert call_args["is_del"] is False
        mock_cursor.sort.assert_called_once_with("create_at", -1)
        mock_cursor.limit.assert_called_once_with(50)

    @pytest.mark.unit
    def test_get_by_user_with_status_filter(self, crud):
        """带状态过滤时查询条件包含 status"""
        mock_collection = crud._driver.get_collection.return_value
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = []
        mock_collection.find.return_value = mock_cursor

        crud.get_by_user("user_123", status=1)

        call_args = mock_collection.find.call_args[0][0]
        assert call_args["status"] == 1

    @pytest.mark.unit
    def test_get_by_status_query_filter(self, crud):
        """验证 get_by_status 查询条件包含 status"""
        mock_collection = crud._driver.get_collection.return_value
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = []
        mock_collection.find.return_value = mock_cursor

        crud.get_by_status(2, limit=30)

        call_args = mock_collection.find.call_args[0][0]
        assert call_args["status"] == 2
        assert call_args["is_del"] is False

    @pytest.mark.unit
    def test_get_recent_failed_delegates_to_get_by_status(self, crud):
        """get_recent_failed 委托 get_by_status 并传入 FAILED 状态"""
        with patch.object(crud, "get_by_status", return_value=[]) as mock_get_by_status:
            crud.get_recent_failed(limit=10)

            mock_get_by_status.assert_called_once()
            # 验证状态值为 FAILED (2)
            call_kwargs = mock_get_by_status.call_args
            assert call_kwargs[1]["status"] == 2  # FAILED
            assert call_kwargs[1]["limit"] == 10


# ============================================================
# update_status 更新状态
# ============================================================


class TestNotificationRecordCRUDUpdateStatus:
    """update_status 更新记录状态测试"""

    @pytest.mark.unit
    def test_update_status_basic(self, crud):
        """验证 update_status 构造正确的 $set 字段"""
        mock_collection = crud._driver.get_collection.return_value
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result

        count = crud.update_status("msg_001", status=1)

        assert count == 1
        mock_collection.update_many.assert_called_once()
        # 验证 filter 条件
        filter_args = mock_collection.update_many.call_args[0][0]
        assert filter_args["message_id"] == "msg_001"
        assert filter_args["is_del"] is False
        # 验证 $set 内容
        set_data = mock_collection.update_many.call_args[0][1]["$set"]
        assert set_data["status"] == 1
        assert "update_at" in set_data

    @pytest.mark.unit
    def test_update_status_with_error_message(self, crud):
        """附带错误信息时 $set 包含 error_message"""
        mock_collection = crud._driver.get_collection.return_value
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result

        crud.update_status("msg_001", status=2, error_message="timeout")

        set_data = mock_collection.update_many.call_args[0][1]["$set"]
        assert set_data["error_message"] == "timeout"

    @pytest.mark.unit
    def test_update_status_sent_adds_sent_at(self, crud):
        """状态为 SENT(1) 时自动添加 sent_at 字段"""
        mock_collection = crud._driver.get_collection.return_value
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result

        crud.update_status("msg_001", status=1)

        set_data = mock_collection.update_many.call_args[0][1]["$set"]
        assert "sent_at" in set_data

    @pytest.mark.unit
    def test_update_status_error_returns_zero(self, crud):
        """异常时返回 0"""
        mock_collection = crud._driver.get_collection.return_value
        mock_collection.update_many.side_effect = Exception("DB error")

        count = crud.update_status("msg_001", status=1)

        assert count == 0
