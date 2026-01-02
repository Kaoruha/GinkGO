# Upstream: None
# Downstream: None
# Role: MNotificationTemplate单元测试验证通知模板模型功能


"""
MNotificationTemplate Unit Tests

测试覆盖:
- 模板初始化
- 枚举处理
- 变量提取和渲染
- MongoDB 转换
"""

import pytest
import json
from datetime import datetime

from ginkgo.data.models import MNotificationTemplate
from ginkgo.enums import TEMPLATE_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestNotificationTemplateInit:
    """MNotificationTemplate 初始化测试"""

    def test_default_init(self):
        """测试默认初始化"""
        template = MNotificationTemplate(
            template_id="test_template",
            template_name="Test Template",
            content="Test content"
        )

        assert template.template_id == "test_template"
        assert template.template_name == "Test Template"
        assert template.template_type == TEMPLATE_TYPES.TEXT.value
        assert template.content == "Test content"
        assert template.subject == ""
        assert template.variables == "{}"
        assert template.is_active is True
        assert template.tags == []
        assert template.__collection__ == "notification_templates"

    def test_init_with_all_fields(self):
        """测试完整字段初始化"""
        variables_dict = {"symbol": "股票代码", "price": "价格"}
        template = MNotificationTemplate(
            template_id="trade_alert",
            template_name="Trade Alert",
            template_type=TEMPLATE_TYPES.MARKDOWN.value,
            subject="Trade Signal: {{symbol}}",
            content="# Signal\n\nSymbol: {{symbol}}\nPrice: {{price}}",
            variables=json.dumps(variables_dict, ensure_ascii=False),
            is_active=True,
            tags=["trading", "alert"]
        )

        assert template.template_id == "trade_alert"
        assert template.template_name == "Trade Alert"
        assert template.template_type == TEMPLATE_TYPES.MARKDOWN.value
        assert template.subject == "Trade Signal: {{symbol}}"
        assert template.tags == ["trading", "alert"]
        assert template.get_variables_dict() == variables_dict

    def test_uuid_auto_generation(self):
        """测试 UUID 自动生成"""
        template1 = MNotificationTemplate(
            template_id="test1",
            template_name="Test 1",
            content="Content 1"
        )
        template2 = MNotificationTemplate(
            template_id="test2",
            template_name="Test 2",
            content="Content 2"
        )

        assert len(template1.uuid) == 32
        assert len(template2.uuid) == 32
        assert template1.uuid != template2.uuid


@pytest.mark.unit
class TestNotificationTemplateValidation:
    """MNotificationTemplate 验证测试"""

    def test_template_type_validation(self):
        """测试模板类型验证"""
        # 有效类型
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test",
            content="Content",
            template_type=TEMPLATE_TYPES.MARKDOWN.value
        )
        assert template.template_type == TEMPLATE_TYPES.MARKDOWN.value

        # 无效类型
        with pytest.raises(ValueError, match="Invalid template_type"):
            MNotificationTemplate(
                template_id="test",
                template_name="Test",
                content="Content",
                template_type=999
            )

    def test_variables_validation_valid(self):
        """测试有效变量 JSON 验证"""
        variables = '{"symbol": "股票代码", "price": "价格"}'
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test",
            content="Content",
            variables=variables
        )
        assert template.variables == variables

    def test_variables_validation_invalid(self):
        """测试无效变量 JSON 验证"""
        with pytest.raises(ValueError, match="variables must be valid JSON"):
            MNotificationTemplate(
                template_id="test",
                template_name="Test",
                content="Content",
                variables="{invalid json}"
            )

    def test_template_id_required(self):
        """测试 template_id 必填"""
        with pytest.raises(Exception):
            MNotificationTemplate(
                template_name="Test",
                content="Content"
            )

    def test_content_required(self):
        """测试 content 必填"""
        with pytest.raises(Exception):
            MNotificationTemplate(
                template_id="test",
                template_name="Test"
            )


@pytest.mark.unit
class TestNotificationTemplateMethods:
    """MNotificationTemplate 方法测试"""

    def test_get_template_type_enum(self):
        """测试获取模板类型枚举"""
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test",
            content="Content",
            template_type=TEMPLATE_TYPES.EMBEDDED.value
        )

        enum_type = template.get_template_type_enum()
        assert enum_type == TEMPLATE_TYPES.EMBEDDED
        assert enum_type.name == "EMBEDDED"

    def test_get_variables_dict(self):
        """测试获取变量字典"""
        variables_dict = {"symbol": "股票代码", "price": "价格"}
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test",
            content="Content",
            variables=json.dumps(variables_dict, ensure_ascii=False)
        )

        result = template.get_variables_dict()
        assert result == variables_dict
        assert result["symbol"] == "股票代码"
        assert result["price"] == "价格"

    def test_set_variables_dict(self):
        """测试设置变量字典"""
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test",
            content="Content"
        )

        variables_dict = {"symbol": "股票代码", "price": "价格"}
        template.set_variables_dict(variables_dict)

        assert template.get_variables_dict() == variables_dict

    def test_get_required_variables(self):
        """测试提取必需变量"""
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test",
            content="# Trade Signal\n\nSymbol: {{symbol}}\nDirection: {{direction}}\nPrice: {{price}}\n\nNote: {{symbol}} again"
        )

        variables = template.get_required_variables()
        assert set(variables) == {"symbol", "direction", "price"}

    def test_get_required_variables_empty(self):
        """测试无变量的模板"""
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test",
            content="Plain text without variables"
        )

        variables = template.get_required_variables()
        assert variables == []

    def test_render_content_success(self):
        """测试成功渲染模板"""
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test",
            content="Symbol: {{symbol}}, Price: {{price}}"
        )

        context = {"symbol": "AAPL", "price": 150.25}
        result = template.render_content(context)

        assert result == "Symbol: AAPL, Price: 150.25"

    def test_render_content_with_markdown(self):
        """测试渲染 Markdown 模板"""
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test",
            template_type=TEMPLATE_TYPES.MARKDOWN.value,
            content="# {{title}}\n\nSymbol: {{symbol}}\nPrice: **{{price}}**"
        )

        context = {"title": "Trade Alert", "symbol": "AAPL", "price": 150.25}
        result = template.render_content(context)

        assert "# Trade Alert" in result
        assert "Symbol: AAPL" in result
        assert "**150.25**" in result

    def test_render_content_missing_variable(self):
        """测试渲染时缺少变量（Jinja2 默认行为）"""
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test",
            content="Symbol: {{symbol}}, Price: {{price}}"
        )

        context = {"symbol": "AAPL"}  # 缺少 price
        result = template.render_content(context)

        # Jinja2 会将未定义变量渲染为空字符串
        assert "Symbol: AAPL" in result


@pytest.mark.unit
class TestNotificationTemplateMongoDB:
    """MNotificationTemplate MongoDB 转换测试"""

    def test_model_dump_mongo(self):
        """测试转换为 MongoDB 文档"""
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test",
            template_type=TEMPLATE_TYPES.MARKDOWN.value,
            subject="Test Subject",
            content="Test content with {{variable}}",
            variables='{"variable": "description"}',
            is_active=True,
            tags=["test", "demo"]
        )

        doc = template.model_dump_mongo()

        assert doc["uuid"] == template.uuid
        assert doc["template_id"] == "test"
        assert doc["template_name"] == "Test"
        assert doc["template_type"] == TEMPLATE_TYPES.MARKDOWN.value
        assert doc["subject"] == "Test Subject"
        assert doc["content"] == "Test content with {{variable}}"
        assert doc["variables"] == '{"variable": "description"}'
        assert doc["is_active"] is True
        assert doc["tags"] == ["test", "demo"]

    def test_from_mongo(self):
        """测试从 MongoDB 文档创建"""
        doc = {
            "uuid": "abc123" * 5,  # 32 chars
            "template_id": "test_template",
            "template_name": "Test Template",
            "template_type": TEMPLATE_TYPES.TEXT.value,
            "subject": "Test Subject",
            "content": "Test content",
            "variables": "{}",
            "is_active": True,
            "tags": [],
            "meta": "{}",
            "desc": "Test description",
            "create_at": datetime.now(),
            "update_at": datetime.now(),
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        template = MNotificationTemplate.from_mongo(doc)

        assert template.uuid == doc["uuid"]
        assert template.template_id == "test_template"
        assert template.template_name == "Test Template"
        assert template.template_type == TEMPLATE_TYPES.TEXT.value

    def test_from_mongo_with_iso_dates(self):
        """测试从 ISO 格式日期字符串创建"""
        doc = {
            "uuid": "abc123" * 5,
            "template_id": "test",
            "template_name": "Test",
            "template_type": TEMPLATE_TYPES.TEXT.value,
            "content": "Content",
            "variables": "{}",
            "is_active": True,
            "tags": [],
            "meta": "{}",
            "desc": "",
            "create_at": "2024-01-01T12:00:00",
            "update_at": "2024-01-01T12:00:00",
            "is_del": False,
            "source": SOURCE_TYPES.OTHER.value
        }

        template = MNotificationTemplate.from_mongo(doc)

        assert isinstance(template.create_at, datetime)
        assert isinstance(template.update_at, datetime)


@pytest.mark.unit
class TestNotificationTemplateRepr:
    """MNotificationTemplate 字符串表示测试"""

    def test_repr_active(self):
        """测试激活状态的字符串表示"""
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test Template",
            content="Content",
            is_active=True
        )

        repr_str = repr(template)
        assert "MNotificationTemplate" in repr_str
        assert "test" in repr_str
        assert "Test Template" in repr_str
        assert "Active" in repr_str

    def test_repr_inactive(self):
        """测试非激活状态的字符串表示"""
        template = MNotificationTemplate(
            template_id="test",
            template_name="Test Template",
            content="Content",
            is_active=False
        )

        repr_str = repr(template)
        assert "Inactive" in repr_str
