"""codes.py 模块单元测试

测试错误码/业务代码工具模块中的纯函数。
"""

import pytest
from ginkgo.libs.utils.codes import cn_index


@pytest.mark.unit
class TestCnIndex:
    """cn_index 函数测试"""

    def test_returns_empty_list(self):
        """cn_index 应返回空列表"""
        result = cn_index()
        assert result == []

    def test_returns_list_type(self):
        """cn_index 返回值类型应为 list"""
        result = cn_index()
        assert isinstance(result, list)

    def test_multiple_calls_return_empty(self):
        """多次调用 cn_index 均应返回空列表"""
        for _ in range(3):
            assert cn_index() == []
