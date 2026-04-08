"""
性能: 219MB RSS, 1.98s, 10 tests [PASS]
GinkgoSourceBase 数据源基类单元测试

测试范围:
1. 构造和属性管理
2. client property getter/setter
3. connect 抽象方法
4. 继承验证
"""

import pytest
from unittest.mock import MagicMock

from ginkgo.data.sources.source_base import GinkgoSourceBase


@pytest.mark.unit
class TestSourceBaseConstruction:
    """测试 GinkgoSourceBase 构造"""

    def test_default_construction(self):
        """默认构造时 client 为 None"""
        base = GinkgoSourceBase()
        assert base.client is None

    def test_construction_with_args(self):
        """接受任意参数不报错"""
        base = GinkgoSourceBase("arg1", "arg2", key="value")
        assert base.client is None

    def test_is_not_abstract(self):
        """基类可直接实例化（非 ABC）"""
        base = GinkgoSourceBase()
        assert base is not None


@pytest.mark.unit
class TestSourceBaseClient:
    """测试 client property"""

    def test_set_client(self):
        """设置 client"""
        base = GinkgoSourceBase()
        mock_client = MagicMock()
        base.client = mock_client
        assert base.client is mock_client

    def test_set_client_none(self):
        """设置 client 为 None"""
        base = GinkgoSourceBase()
        base.client = MagicMock()
        base.client = None
        assert base.client is None

    def test_set_client_string(self):
        """client 可以是任意类型"""
        base = GinkgoSourceBase()
        base.client = "test_client"
        assert base.client == "test_client"


@pytest.mark.unit
class TestSourceBaseConnect:
    """测试 connect 抽象方法"""

    def test_connect_raises_not_implemented(self):
        """基类 connect 方法应抛出 NotImplementedError"""
        base = GinkgoSourceBase()
        with pytest.raises(NotImplementedError):
            base.connect()

    def test_connect_with_args_raises(self):
        """带参数调用同样抛出 NotImplementedError"""
        base = GinkgoSourceBase()
        with pytest.raises(NotImplementedError):
            base.connect(host="localhost", port=3306)


@pytest.mark.unit
class TestSourceBaseInheritance:
    """测试继承行为"""

    def test_subclass_can_override_connect(self):
        """子类可以覆盖 connect"""
        class MySource(GinkgoSourceBase):
            def connect(self, *args, **kwargs):
                self._client = "connected"

        src = MySource()
        src.connect()
        assert src.client == "connected"

    def test_subclass_can_override_client(self):
        """子类可以在构造中设置 client"""
        class MySource(GinkgoSourceBase):
            def __init__(self):
                super().__init__()
                self.client = "pre-connected"

        src = MySource()
        assert src.client == "pre-connected"
