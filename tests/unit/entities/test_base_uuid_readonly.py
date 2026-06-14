"""Base.uuid 只读保护测试（ADR-010 §5 V10：身份不变量创建后只读）。

删 Base.uuid.setter + set_uuid 后，运行时 ``.uuid=`` 抛 AttributeError；
uuid 走 ``Base.__init__(uuid=...)`` 构造注入，未传时自动生成（带 prefix）。
"""
import pytest

from ginkgo.entities.base import Base


class TestBaseUuidReadonly:
    """Base.uuid 创建后只读（ADR-010 V10 身份不变量）。"""

    def test_uuid_setter_removed(self):
        """运行时 .uuid= 抛 AttributeError（封装落地）。"""
        b = Base()
        with pytest.raises(AttributeError):
            b.uuid = "should-fail"

    def test_set_uuid_method_removed(self):
        """set_uuid() 已删（业务零调用，ADR-010 §5）。"""
        b = Base()
        assert not hasattr(b, "set_uuid"), "set_uuid 应已删除"

    def test_uuid_constructor_injection(self):
        """uuid 走构造注入（Base.__init__ uuid 参数）。"""
        b = Base(uuid="injected-uuid-123")
        assert b.uuid == "injected-uuid-123"

    def test_uuid_auto_generated_when_not_provided(self):
        """未传 uuid 时 Base.__init__ 自动生成（带 prefix，非空）。"""
        b = Base()
        assert b.uuid and len(b.uuid) > 0
