"""
性能: 219MB RSS, 1.89s, 16 tests [PASS]
"""

# Upstream: BaseMongoCRUD (继承)、MNotificationTemplate (模型)
# Downstream: None (单元测试)
# Role: NotificationTemplateCRUD 通知模板 CRUD 单元测试（Mock MongoDB 驱动）


"""
NotificationTemplateCRUD 单元测试（Mock MongoDB 驱动）

覆盖范围：
- 构造与类型检查：model_class、driver 绑定
- add：添加模板（含重复检测）、失败场景
- get_by_template_id：按模板ID查询，验证查询条件
- get_by_template_name：按名称模糊查询，验证正则表达式
- get_active_templates：获取启用模板，验证过滤条件
- update_by_template_id：按模板ID更新，验证 $set 字段
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


# ============================================================
# 辅助：构造 NotificationTemplateCRUD 实例（mock MongoDB 驱动）
# ============================================================


@pytest.fixture
def mock_driver():
    """mock GinkgoMongo 驱动"""
    driver = MagicMock()
    driver.get_collection.return_value = MagicMock()
    return driver


@pytest.fixture
def crud(mock_driver):
    """构造 NotificationTemplateCRUD 实例，注入 mock 驱动"""
    with patch("ginkgo.data.crud.base_mongo_crud.GLOG", MagicMock()), \
         patch("ginkgo.data.crud.notification_template_crud.GLOG", MagicMock()), \
         patch("ginkgo.data.crud.base_mongo_crud.ModelCRUDMapping.register"):
        from ginkgo.data.crud.notification_template_crud import NotificationTemplateCRUD
        from ginkgo.data.models.model_notification_template import MNotificationTemplate
        return NotificationTemplateCRUD(
            model_class=MNotificationTemplate,
            driver=mock_driver,
        )


@pytest.fixture
def fake_template():
    """构造假的 MNotificationTemplate"""
    tmpl = MagicMock()
    tmpl.uuid = "fake_tmpl_uuid"
    tmpl.template_id = "trade_alert"
    tmpl.model_dump_for_mongo.return_value = {
        "uuid": "fake_tmpl_uuid",
        "template_id": "trade_alert",
    }
    return tmpl


# ============================================================
# 构造与类型检查
# ============================================================


class TestNotificationTemplateCRUDConstruction:
    """NotificationTemplateCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_model_class_is_correct(self, crud):
        """验证 model_class 为 MNotificationTemplate"""
        from ginkgo.data.models.model_notification_template import MNotificationTemplate
        assert crud.model_class is MNotificationTemplate

    @pytest.mark.unit
    def test_driver_is_bound(self, crud, mock_driver):
        """验证 driver 正确绑定"""
        assert crud._driver is mock_driver

    @pytest.mark.unit
    def test_class_level_model_class(self):
        """类属性 _model_class 正确设置"""
        with patch("ginkgo.data.crud.base_mongo_crud.GLOG", MagicMock()), \
             patch("ginkgo.data.crud.base_mongo_crud.ModelCRUDMapping.register"):
            from ginkgo.data.crud.notification_template_crud import NotificationTemplateCRUD
            from ginkgo.data.models.model_notification_template import MNotificationTemplate
            assert NotificationTemplateCRUD._model_class is MNotificationTemplate


# ============================================================
# add 添加模板
# ============================================================


class TestNotificationTemplateCRUDAdd:
    """add 添加通知模板测试"""

    @pytest.mark.unit
    def test_add_success(self, crud, fake_template):
        """添加成功返回 UUID（无重复）"""
        with patch.object(crud, "get_by_template_id", return_value=None):
            with patch.object(crud.__class__.__bases__[0], "add", return_value="fake_tmpl_uuid"):
                result = crud.add(fake_template)
                assert result == "fake_tmpl_uuid"

    @pytest.mark.unit
    def test_add_duplicate_returns_none(self, crud, fake_template):
        """template_id 已存在时返回 None"""
        mock_existing = MagicMock()
        with patch.object(crud, "get_by_template_id", return_value=mock_existing):
            result = crud.add(fake_template)
            assert result is None

    @pytest.mark.unit
    def test_add_exception_returns_none(self, crud, fake_template):
        """异常时返回 None"""
        with patch.object(crud, "get_by_template_id", return_value=None):
            with patch.object(crud.__class__.__bases__[0], "add", side_effect=Exception("DB error")):
                result = crud.add(fake_template)
                assert result is None


# ============================================================
# get_by_template_id 按模板ID查询
# ============================================================


class TestNotificationTemplateCRUDGetByTemplateId:
    """get_by_template_id 按模板ID查询测试"""

    @pytest.mark.unit
    def test_query_with_correct_filter(self, crud):
        """验证查询条件包含 template_id 和 is_del=False"""
        mock_collection = crud._driver.get_collection.return_value
        mock_collection.find_one.return_value = None

        crud.get_by_template_id("trade_alert")

        mock_collection.find_one.assert_called_once()
        call_args = mock_collection.find_one.call_args[0][0]
        assert call_args["template_id"] == "trade_alert"
        assert call_args["is_del"] is False

    @pytest.mark.unit
    def test_returns_none_when_not_found(self, crud):
        """未找到模板返回 None"""
        mock_collection = crud._driver.get_collection.return_value
        mock_collection.find_one.return_value = None

        result = crud.get_by_template_id("nonexistent")

        assert result is None


# ============================================================
# get_by_template_name / get_active_templates
# ============================================================


class TestNotificationTemplateCRUDQueries:
    """按名称/启用状态查询测试"""

    @pytest.mark.unit
    def test_get_by_template_name_uses_regex(self, crud):
        """验证 get_by_template_name 使用正则表达式查询"""
        mock_collection = crud._driver.get_collection.return_value
        mock_cursor = MagicMock()
        mock_cursor.to_list.return_value = []
        mock_collection.find.return_value = mock_cursor

        crud.get_by_template_name("交易信号")

        call_args = mock_collection.find.call_args[0][0]
        # 验证正则表达式条件
        regex = call_args["template_name"]
        assert "$regex" in regex
        assert regex["$regex"] == "交易信号"
        assert regex["$options"] == "i"  # 不区分大小写
        assert call_args["is_del"] is False

    @pytest.mark.unit
    def test_get_active_templates_query_filter(self, crud):
        """验证 get_active_templates 查询条件包含 is_active=True"""
        mock_collection = crud._driver.get_collection.return_value
        mock_cursor = MagicMock()
        mock_cursor.to_list.return_value = []
        mock_collection.find.return_value = mock_cursor

        crud.get_active_templates()

        call_args = mock_collection.find.call_args[0][0]
        assert call_args["is_active"] is True
        assert call_args["is_del"] is False

    @pytest.mark.unit
    def test_get_active_templates_with_type_filter(self, crud):
        """带模板类型过滤时查询条件包含 template_type"""
        mock_collection = crud._driver.get_collection.return_value
        mock_cursor = MagicMock()
        mock_cursor.to_list.return_value = []
        mock_collection.find.return_value = mock_cursor

        crud.get_active_templates(template_type=2)

        call_args = mock_collection.find.call_args[0][0]
        assert call_args["template_type"] == 2

    @pytest.mark.unit
    def test_get_by_user_empty_result(self, crud):
        """无匹配时返回空列表"""
        mock_collection = crud._driver.get_collection.return_value
        mock_cursor = MagicMock()
        mock_cursor.to_list.return_value = []
        mock_collection.find.return_value = mock_cursor

        result = crud.get_by_template_name("不存在")

        assert result == []


# ============================================================
# update_by_template_id 按模板ID更新
# ============================================================


class TestNotificationTemplateCRUDUpdate:
    """update_by_template_id 按模板ID更新测试"""

    @pytest.mark.unit
    def test_update_basic_fields(self, crud):
        """验证更新时构造正确的 $set 字段"""
        mock_collection = crud._driver.get_collection.return_value
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result

        count = crud.update_by_template_id(
            "trade_alert",
            content="新内容",
            subject="新主题",
        )

        assert count == 1
        # 验证 filter 条件
        filter_args = mock_collection.update_many.call_args[0][0]
        assert filter_args["template_id"] == "trade_alert"
        assert filter_args["is_del"] is False
        # 验证 $set 内容
        set_data = mock_collection.update_many.call_args[0][1]["$set"]
        assert set_data["content"] == "新内容"
        assert set_data["subject"] == "新主题"
        assert "update_at" in set_data

    @pytest.mark.unit
    def test_update_deactivate_template(self, crud):
        """停用模板时 is_active 字段更新为 False"""
        mock_collection = crud._driver.get_collection.return_value
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result

        crud.update_by_template_id("trade_alert", is_active=False)

        set_data = mock_collection.update_many.call_args[0][1]["$set"]
        assert set_data["is_active"] is False

    @pytest.mark.unit
    def test_update_none_fields_ignored(self, crud):
        """值为 None 的字段不包含在 $set 中"""
        mock_collection = crud._driver.get_collection.return_value
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_collection.update_many.return_value = mock_result

        crud.update_by_template_id("trade_alert")

        set_data = mock_collection.update_many.call_args[0][1]["$set"]
        # 只应包含 update_at，不应有 content/subject 等
        assert "content" not in set_data
        assert "subject" not in set_data
        assert "update_at" in set_data

    @pytest.mark.unit
    def test_update_error_returns_zero(self, crud):
        """异常时返回 0"""
        mock_collection = crud._driver.get_collection.return_value
        mock_collection.update_many.side_effect = Exception("DB error")

        count = crud.update_by_template_id("trade_alert", content="test")

        assert count == 0
