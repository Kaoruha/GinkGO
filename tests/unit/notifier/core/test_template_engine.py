# Upstream: None
# Downstream: None
# Role: TemplateEngine单元测试验证模板渲染引擎功能


"""
Template Engine Unit Tests

测试覆盖:
- 基本模板渲染
- 从 template_id 渲染
- 模板验证
- 变量提取
- 错误处理
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ginkgo.notifier.core.template_engine import TemplateEngine
from ginkgo.data.models.model_notification_template import MNotificationTemplate
from ginkgo.enums import TEMPLATE_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestTemplateEngineInit:
    """TemplateEngine 初始化测试"""

    def test_init_without_crud(self):
        """测试无 CRUD 初始化"""
        engine = TemplateEngine()
        assert engine.template_crud is None

    def test_init_with_crud(self):
        """测试带 CRUD 初始化"""
        mock_crud = Mock()
        engine = TemplateEngine(template_crud=mock_crud)
        assert engine.template_crud == mock_crud


@pytest.mark.unit
class TestTemplateEngineRender:
    """TemplateEngine 渲染测试"""

    def test_render_simple_template(self):
        """测试简单模板渲染"""
        engine = TemplateEngine()
        content = "Hello, {{ name }}!"
        context = {"name": "World"}

        result = engine.render(content, context)

        assert result == "Hello, World!"

    def test_render_with_multiple_variables(self):
        """测试多变量模板"""
        engine = TemplateEngine()
        content = "Symbol: {{ symbol }}, Price: {{ price }}, Direction: {{ direction }}"
        context = {
            "symbol": "AAPL",
            "price": 150.25,
            "direction": "LONG"
        }

        result = engine.render(content, context)

        assert "Symbol: AAPL" in result
        assert "Price: 150.25" in result
        assert "Direction: LONG" in result

    def test_render_markdown_template(self):
        """测试 Markdown 模板"""
        engine = TemplateEngine()
        content = "# {{ title }}\n\n**Symbol**: {{ symbol }}\n**Price**: ${{ price }}"
        context = {
            "title": "Trade Alert",
            "symbol": "TSLA",
            "price": 200
        }

        result = engine.render(content, context)

        assert "# Trade Alert" in result
        assert "**Symbol**: TSLA" in result
        assert "**Price**: $200" in result

    def test_render_with_missing_variable(self):
        """测试缺少变量（非严格模式）"""
        engine = TemplateEngine()
        content = "Hello, {{ name }}! Age: {{ age }}"
        context = {"name": "Alice"}  # 缺少 age

        result = engine.render(content, context, strict=False)

        assert "Hello, Alice!" in result
        # 缺少的变量渲染为空字符串

    def test_render_strict_mode_with_missing_variable(self):
        """测试严格模式下缺少变量"""
        engine = TemplateEngine()
        content = "Hello, {{ name }}! Age: {{ age }}"
        context = {"name": "Alice"}  # 缺少 age

        with pytest.raises(ValueError, match="Template rendering error"):
            engine.render(content, context, strict=True)

    def test_render_with_loops(self):
        """测试循环渲染"""
        engine = TemplateEngine()
        content = "{% for item in items %}{{ item }} {% endfor %}"
        context = {"items": ["A", "B", "C"]}

        result = engine.render(content, context)

        assert "A" in result
        assert "B" in result
        assert "C" in result

    def test_render_with_conditionals(self):
        """测试条件渲染"""
        engine = TemplateEngine()
        content = "{% if show_price %}Price: {{ price }}{% endif %}"
        context = {"show_price": True, "price": 100}

        result = engine.render(content, context)

        assert "Price: 100" in result

    def test_render_syntax_error(self):
        """测试语法错误"""
        engine = TemplateEngine()
        content = "Hello, {{ name }!"  # 缺少闭合括号

        with pytest.raises(ValueError, match="Template syntax error"):
            engine.render(content, {"name": "Test"})


@pytest.mark.unit
class TestTemplateEngineRenderFromTemplateId:
    """TemplateEngine 从 template_id 渲染测试"""

    def test_render_from_template_id_success(self):
        """测试成功从 template_id 渲染"""
        mock_crud = Mock()
        template = MNotificationTemplate(
            template_id="test_template",
            template_name="Test",
            content="Hello, {{ name }}!",
            is_active=True
        )
        mock_crud.get_by_template_id.return_value = template

        engine = TemplateEngine(template_crud=mock_crud)

        result = engine.render_from_template_id("test_template", {"name": "World"})

        assert result == "Hello, World!"
        mock_crud.get_by_template_id.assert_called_once_with("test_template")

    def test_render_from_template_id_not_found(self):
        """测试模板不存在"""
        mock_crud = Mock()
        mock_crud.get_by_template_id.return_value = None

        engine = TemplateEngine(template_crud=mock_crud)

        with pytest.raises(ValueError, match="Template not found"):
            engine.render_from_template_id("nonexistent", {})

    def test_render_from_template_id_not_active(self):
        """测试模板未启用"""
        mock_crud = Mock()
        template = MNotificationTemplate(
            template_id="inactive_template",
            template_name="Inactive",
            content="Content",
            is_active=False
        )
        mock_crud.get_by_template_id.return_value = template

        engine = TemplateEngine(template_crud=mock_crud)

        with pytest.raises(ValueError, match="Template is not active"):
            engine.render_from_template_id("inactive_template", {})

    def test_render_from_template_id_without_crud(self):
        """测试无 CRUD 实例"""
        engine = TemplateEngine(template_crud=None)

        with pytest.raises(ValueError, match="template_crud is not initialized"):
            engine.render_from_template_id("test", {})


@pytest.mark.unit
class TestTemplateEngineValidate:
    """TemplateEngine 验证测试"""

    def test_validate_valid_template(self):
        """测试验证有效模板"""
        engine = TemplateEngine()
        content = "Hello, {{ name }}!"

        result = engine.validate_template(content)

        assert result["valid"] is True
        assert result["error"] is None
        assert "name" in result["variables"]

    def test_validate_syntax_error(self):
        """测试验证语法错误"""
        engine = TemplateEngine()
        content = "Hello, {{ name }!"  # 语法错误

        result = engine.validate_template(content)

        assert result["valid"] is False
        assert result["error"] is not None
        assert "syntax error" in result["error"].lower()

    def test_extract_variables(self):
        """测试变量提取"""
        engine = TemplateEngine()
        content = "Symbol: {{ symbol }}, Price: {{ price }}, Direction: {{ direction }}"

        result = engine.validate_template(content)

        assert "symbol" in result["variables"]
        assert "price" in result["variables"]
        assert "direction" in result["variables"]


@pytest.mark.unit
class TestTemplateEngineRenderWithDefaults:
    """TemplateEngine 默认值渲染测试"""

    def test_render_with_defaults(self):
        """测试使用默认值渲染"""
        engine = TemplateEngine()
        content = "Name: {{ name }}, Age: {{ age }}"
        context = {"name": "Alice"}
        defaults = {"age": "Unknown"}

        result = engine.render_with_defaults(content, context, defaults)

        assert "Name: Alice" in result
        assert "Age: Unknown" in result

    def test_render_with_defaults_override(self):
        """测试 context 覆盖默认值"""
        engine = TemplateEngine()
        content = "Name: {{ name }}, Age: {{ age }}"
        context = {"name": "Bob", "age": 30}
        defaults = {"age": 0, "city": "Unknown"}

        result = engine.render_with_defaults(content, context, defaults)

        assert "Name: Bob" in result
        assert "Age: 30" in result


@pytest.mark.unit
class TestTemplateEnginePreview:
    """TemplateEngine 预览测试"""

    def test_preview_template(self):
        """测试预览模板"""
        mock_crud = Mock()
        template = MNotificationTemplate(
            template_id="preview_test",
            template_name="Preview Test",
            template_type=TEMPLATE_TYPES.MARKDOWN.value,
            content="# {{ title }}\n\nSymbol: {{ symbol }}",
            is_active=True
        )
        mock_crud.get_by_template_id.return_value = template

        engine = TemplateEngine(template_crud=mock_crud)

        result = engine.preview_template("preview_test")

        assert result["template_id"] == "preview_test"
        assert result["template_name"] == "Preview Test"
        assert result["template_type"] == "MARKDOWN"
        assert "# <title>" in result["rendered"]
        assert "symbol" in result["variables"]

    def test_preview_template_with_context(self):
        """测试带上下文的预览"""
        mock_crud = Mock()
        template = MNotificationTemplate(
            template_id="preview_test",
            template_name="Preview Test",
            content="Hello, {{ name }}!",
            is_active=True
        )
        mock_crud.get_by_template_id.return_value = template

        engine = TemplateEngine(template_crud=mock_crud)

        result = engine.preview_template("preview_test", context={"name": "Alice"})

        assert "Hello, Alice!" in result["rendered"]
        assert result["context_used"]["name"] == "Alice"


@pytest.mark.unit
class TestTemplateEngineBatchRender:
    """TemplateEngine 批量渲染测试"""

    def test_batch_render(self):
        """测试批量渲染"""
        engine = TemplateEngine()
        content = "Name: {{ name }}, Age: {{ age }}"
        contexts = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
            {"name": "Charlie", "age": 35}
        ]

        results = engine.batch_render(content, contexts)

        assert len(results) == 3
        assert "Name: Alice" in results[0]
        assert "Name: Bob" in results[1]
        assert "Name: Charlie" in results[2]

    def test_batch_render_with_error(self):
        """测试批量渲染包含错误"""
        engine = TemplateEngine()
        content = "Name: {{ name }}, Age: {{ age }}"
        contexts = [
            {"name": "Alice", "age": 30},
            {"name": "Bob"},  # 缺少 age
            {"name": "Charlie", "age": 35}
        ]

        results = engine.batch_render(content, contexts)

        assert len(results) == 3
        assert "Name: Alice" in results[0]
        assert "Name: Bob" in results[1]
        # 错误处理会记录，但不会中断
        assert "Name: Charlie" in results[2]
