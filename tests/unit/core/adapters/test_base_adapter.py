"""
基础适配器单元测试

测试 BaseAdapter、ChainableAdapter、CompositeAdapter、ConditionalAdapter、AdapterError，
验证适配逻辑、链式调用、组合适配、条件选择等行为。
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from ginkgo.core.adapters.base_adapter import (
    AdapterError,
    BaseAdapter,
    ChainableAdapter,
    CompositeAdapter,
    ConditionalAdapter,
)


# ── 具体实现用于测试抽象类 ──────────────────────────────────────────


class ConcreteAdapter(BaseAdapter):
    """BaseAdapter 的具体实现"""

    def __init__(self, name="ConcreteAdapter", supported_types=None):
        super().__init__(name)
        self._supported_types = supported_types or []

    def can_adapt(self, source, target_type=None):
        if target_type is None:
            return source is not None
        return target_type in self._supported_types

    def adapt(self, source, target_type=None, **kwargs):
        return f"adapted_{source}"


class StringToIntAdapter(BaseAdapter):
    """字符串转整数适配器"""

    def can_adapt(self, source, target_type=None):
        return isinstance(source, str)

    def adapt(self, source, target_type=None, **kwargs):
        return int(source)


class IntToStrAdapter(BaseAdapter):
    """整数转字符串适配器"""

    def can_adapt(self, source, target_type=None):
        return isinstance(source, int)

    def adapt(self, source, target_type=None, **kwargs):
        return str(source)


class ConcreteChainableAdapter(ChainableAdapter):
    """ChainableAdapter 的具体实现（继承抽象方法）"""

    def __init__(self, name="ConcreteChainableAdapter"):
        super().__init__(name)

    def can_adapt(self, source, target_type=None):
        return source is not None

    def adapt(self, source, target_type=None, **kwargs):
        return f"adapted_{source}"


# ── AdapterError 测试 ───────────────────────────────────────────────


@pytest.mark.unit
class TestAdapterError:
    """AdapterError 异常测试"""

    def test_is_exception(self):
        """是 Exception 子类"""
        assert issubclass(AdapterError, Exception)

    def test_message(self):
        """异常消息"""
        err = AdapterError("适配失败")
        assert str(err) == "适配失败"

    def test_can_be_raised(self):
        """可以抛出"""
        with pytest.raises(AdapterError):
            raise AdapterError("test")


# ── BaseAdapter 构造测试 ────────────────────────────────────────────


@pytest.mark.unit
class TestBaseAdapterConstruction:
    """BaseAdapter 构造测试"""

    def test_default_construction(self):
        """默认构造"""
        adapter = ConcreteAdapter()
        assert adapter.name == "ConcreteAdapter"
        assert adapter.created_at is not None
        assert adapter.adapted_count == 0

    def test_custom_name(self):
        """自定义名称"""
        adapter = ConcreteAdapter(name="MyAdapter")
        assert adapter.name == "MyAdapter"

    def test_initial_error_count_zero(self):
        """初始错误计数为 0"""
        adapter = ConcreteAdapter()
        assert adapter.error_count == 0

    def test_initial_error_log_empty(self):
        """初始错误日志为空"""
        adapter = ConcreteAdapter()
        assert adapter.error_log == []


# ── BaseAdapter 验证测试 ────────────────────────────────────────────


@pytest.mark.unit
class TestBaseAdapterValidation:
    """BaseAdapter 验证方法测试"""

    def test_validate_source_none_returns_false(self):
        """None 源对象无效"""
        adapter = ConcreteAdapter()
        assert adapter.validate_source(None) is False

    def test_validate_source_non_none_returns_true(self):
        """非 None 源对象有效"""
        adapter = ConcreteAdapter()
        assert adapter.validate_source("source") is True

    def test_validate_target_type_none_returns_false(self):
        """None 目标类型无效"""
        adapter = ConcreteAdapter()
        assert adapter.validate_target_type(None) is False

    def test_validate_target_type_non_none_returns_true(self):
        """非 None 目标类型有效"""
        adapter = ConcreteAdapter()
        assert adapter.validate_target_type(str) is True


# ── BaseAdapter 日志和统计测试 ──────────────────────────────────────


@pytest.mark.unit
class TestBaseAdapterLogging:
    """BaseAdapter 日志和统计测试"""

    def test_log_adaptation_success(self):
        """成功适配递增计数"""
        adapter = ConcreteAdapter()
        adapter.log_adaptation("source", "target", success=True)
        assert adapter.adapted_count == 1
        assert adapter.error_count == 0

    def test_log_adaptation_failure(self):
        """失败适配递增错误计数"""
        adapter = ConcreteAdapter()
        adapter.log_adaptation("source", None, success=False, error="test error")
        assert adapter.error_count == 1
        assert len(adapter.error_log) == 1
        assert adapter.error_log[0]["error"] == "test error"

    def test_log_adaptation_failure_record_structure(self):
        """失败日志记录结构"""
        adapter = ConcreteAdapter()
        adapter.log_adaptation("source", None, success=False, error="err")
        record = adapter.error_log[0]
        assert "timestamp" in record
        assert "source_type" in record
        assert record["error"] == "err"
        assert "source_repr" in record

    def test_clear_error_log(self):
        """清空错误日志"""
        adapter = ConcreteAdapter()
        adapter.log_adaptation("s", None, success=False, error="e")
        adapter.clear_error_log()
        assert adapter.error_count == 0
        assert adapter.error_log == []

    def test_get_adaptation_stats(self):
        """获取适配统计"""
        adapter = ConcreteAdapter()
        adapter.log_adaptation("s", "t", success=True)
        adapter.log_adaptation("s", None, success=False, error="e")
        stats = adapter.get_adaptation_stats()
        assert stats["name"] == "ConcreteAdapter"
        assert stats["adapted_count"] == 1
        assert stats["error_count"] == 1
        assert stats["success_rate"] == 0.5
        assert "created_at" in stats

    def test_get_adaptation_stats_empty(self):
        """空统计的成功率为 0.0"""
        adapter = ConcreteAdapter()
        stats = adapter.get_adaptation_stats()
        assert stats["success_rate"] == 0.0

    def test_reset_stats(self):
        """重置统计"""
        adapter = ConcreteAdapter()
        adapter.log_adaptation("s", "t", success=True)
        adapter.log_adaptation("s", None, success=False, error="e")
        adapter.reset_stats()
        assert adapter.adapted_count == 0
        assert adapter.error_count == 0

    def test_str_representation(self):
        """字符串表示"""
        adapter = ConcreteAdapter()
        s = str(adapter)
        assert "ConcreteAdapter" in s

    def test_repr_equals_str(self):
        """repr 与 str 相同"""
        adapter = ConcreteAdapter()
        assert repr(adapter) == str(adapter)


# ── ChainableAdapter 测试 ───────────────────────────────────────────


@pytest.mark.unit
class TestChainableAdapter:
    """可链式调用适配器测试"""

    def test_set_next_returns_adapter(self):
        """设置下一个适配器返回该适配器"""
        first = ConcreteChainableAdapter(name="first")
        second = ConcreteChainableAdapter(name="second")
        result = first.set_next(second)
        assert result is second
        assert first._next_adapter is second

    def test_adapt_chain_current_can_adapt(self):
        """当前适配器可以处理时直接返回"""
        adapter = ConcreteChainableAdapter()
        result = adapter.adapt_chain("42")
        assert result == "adapted_42"
        assert adapter.adapted_count == 1

    def test_adapt_chain_falls_to_next(self):
        """当前适配器无法处理时转发到下一个"""
        first = ConcreteChainableAdapter(name="first")
        # 让第一个无法处理 int
        original_can = first.can_adapt
        first.can_adapt = lambda source, target_type=None: isinstance(source, str)

        second = ConcreteChainableAdapter(name="second")
        first.set_next(second)

        result = first.adapt_chain(42)
        assert result == "adapted_42"  # 由 second 处理

    def test_adapt_chain_no_adapter_raises(self):
        """无可用适配器抛出异常"""
        adapter = ConcreteChainableAdapter()
        # 让 can_adapt 总是返回 False
        adapter.can_adapt = MagicMock(return_value=False)
        with pytest.raises(AdapterError, match="无法将"):
            adapter.adapt_chain(42)

    def test_adapt_chain_error_logs_failure(self):
        """链式适配失败记录错误"""
        adapter = ConcreteChainableAdapter()
        adapter.can_adapt = MagicMock(return_value=False)
        try:
            adapter.adapt_chain(42)
        except AdapterError:
            pass
        assert adapter.error_count == 1


# ── CompositeAdapter 测试 ───────────────────────────────────────────


@pytest.mark.unit
class TestCompositeAdapter:
    """组合适配器测试"""

    def test_add_adapter(self):
        """添加子适配器"""
        composite = CompositeAdapter()
        sub = StringToIntAdapter()
        composite.add_adapter(sub)
        assert len(composite._sub_adapters) == 1

    def test_add_adapter_no_duplicate(self):
        """不重复添加"""
        composite = CompositeAdapter()
        sub = StringToIntAdapter()
        composite.add_adapter(sub)
        composite.add_adapter(sub)
        assert len(composite._sub_adapters) == 1

    def test_remove_adapter(self):
        """移除子适配器"""
        composite = CompositeAdapter()
        sub = StringToIntAdapter()
        composite.add_adapter(sub)
        result = composite.remove_adapter(sub)
        assert result is True
        assert len(composite._sub_adapters) == 0

    def test_remove_nonexistent_adapter(self):
        """移除不存在的适配器返回 False"""
        composite = CompositeAdapter()
        result = composite.remove_adapter(StringToIntAdapter())
        assert result is False

    def test_can_adapt_checks_all_sub_adapters(self):
        """can_adapt 检查所有子适配器"""
        composite = CompositeAdapter()
        composite.add_adapter(StringToIntAdapter())
        assert composite.can_adapt("42", int) is True
        assert composite.can_adapt(42, str) is False

    def test_adapt_uses_first_matching(self):
        """使用第一个匹配的子适配器"""
        composite = CompositeAdapter()
        composite.add_adapter(StringToIntAdapter())
        result = composite.adapt("42")
        assert result == 42

    def test_adapt_falls_to_next_on_failure(self):
        """第一个失败时尝试下一个"""
        failing = ConcreteAdapter(name="failing")
        failing.can_adapt = MagicMock(return_value=True)
        failing.adapt = MagicMock(side_effect=Exception("fail"))

        working = StringToIntAdapter()
        working.can_adapt = MagicMock(return_value=True)

        composite = CompositeAdapter()
        composite.add_adapter(failing)
        composite.add_adapter(working)

        result = composite.adapt("42")
        assert result == 42

    def test_adapt_no_matching_raises(self):
        """无匹配子适配器抛出异常"""
        composite = CompositeAdapter()
        with pytest.raises(AdapterError):
            composite.adapt("source")

    def test_get_sub_adapter_stats(self):
        """获取子适配器统计"""
        composite = CompositeAdapter()
        sub = StringToIntAdapter()
        composite.add_adapter(sub)
        stats = composite.get_sub_adapter_stats()
        assert len(stats) == 1

    def test_get_adaptation_stats_includes_sub_count(self):
        """统计包含子适配器数量"""
        composite = CompositeAdapter()
        composite.add_adapter(StringToIntAdapter())
        stats = composite.get_adaptation_stats()
        assert stats["sub_adapters_count"] == 1
        assert "sub_adapters" in stats


# ── ConditionalAdapter 测试 ─────────────────────────────────────────


@pytest.mark.unit
class TestConditionalAdapter:
    """条件适配器测试"""

    def test_add_condition(self):
        """添加条件"""
        adapter = ConditionalAdapter()
        condition = lambda src, tgt: isinstance(src, str)
        sub = StringToIntAdapter()
        adapter.add_condition(condition, sub)
        assert len(adapter._conditions) == 1

    def test_set_default_adapter(self):
        """设置默认适配器"""
        adapter = ConditionalAdapter()
        default = IntToStrAdapter()
        adapter.set_default_adapter(default)
        assert adapter._default_adapter is default

    def test_can_adapt_no_conditions(self):
        """无条件时不能适配"""
        adapter = ConditionalAdapter()
        assert adapter.can_adapt("source") is False

    def test_can_adapt_condition_matches(self):
        """条件匹配时可以适配"""
        adapter = ConditionalAdapter()
        condition = lambda src, tgt: isinstance(src, str)
        sub = StringToIntAdapter()
        adapter.add_condition(condition, sub)
        assert adapter.can_adapt("42") is True

    def test_can_adapt_default_adapter(self):
        """默认适配器可以适配"""
        adapter = ConditionalAdapter()
        adapter.set_default_adapter(StringToIntAdapter())
        assert adapter.can_adapt("42") is True

    def test_adapt_uses_matching_condition(self):
        """使用匹配条件的适配器"""
        adapter = ConditionalAdapter()
        condition = lambda src, tgt: isinstance(src, str)
        sub = StringToIntAdapter()
        adapter.add_condition(condition, sub)
        result = adapter.adapt("42")
        assert result == 42

    def test_adapt_falls_to_default(self):
        """条件不匹配时使用默认适配器"""
        adapter = ConditionalAdapter()
        condition = lambda src, tgt: False  # 永不匹配
        sub = StringToIntAdapter()
        adapter.add_condition(condition, sub)

        default = IntToStrAdapter()
        adapter.set_default_adapter(default)

        result = adapter.adapt(42)
        assert result == "42"

    def test_adapt_no_adapter_raises(self):
        """无适配器抛出异常"""
        adapter = ConditionalAdapter()
        with pytest.raises(AdapterError):
            adapter.adapt("source")

    def test_adapt_condition_failure_falls_to_next(self):
        """条件适配失败时尝试下一个条件"""
        adapter = ConditionalAdapter()

        failing = ConcreteAdapter(name="failing")
        failing.can_adapt = MagicMock(return_value=True)
        failing.adapt = MagicMock(side_effect=Exception("fail"))

        condition1 = lambda src, tgt: True
        condition2 = lambda src, tgt: True
        working = StringToIntAdapter()
        working.can_adapt = MagicMock(return_value=True)

        adapter.add_condition(condition1, failing)
        adapter.add_condition(condition2, working)

        result = adapter.adapt("42")
        assert result == 42
