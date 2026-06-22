# Upstream: src/ginkgo/services/logging/log_service.py
# Context: #5521 — search_logs LIKE 查询未转义用户输入的 %/_，搜 "%" 返全部记录。
#          提取 _escape_like 纯函数便于单测转义行为（无需 ClickHouse session）。
import pytest

from ginkgo.services.logging.log_service import _escape_like


class TestEscapeLike:
    """LIKE 特殊字符转义（ClickHouse 默认 `\` 为 ESCAPE 字符）。"""

    def test_passthrough_normal_keyword(self):
        # 无特殊字符原样返回
        assert _escape_like("ERROR") == "ERROR"

    def test_escape_percent(self):
        # % 是 LIKE 通配（匹配任意序列），须转义
        assert _escape_like("a%b") == "a\\%b"

    def test_escape_underscore(self):
        # _ 是 LIKE 通配（匹配单字符），须转义
        assert _escape_like("a_b") == "a\\_b"

    def test_escape_backslash_first(self):
        # 反斜杠本身先转义，避免后续转义符被二次解释
        assert _escape_like("a\\b") == "a\\\\b"

    def test_escape_combined_all_special(self):
        assert _escape_like("%_\\") == "\\%\\_\\\\"

    def test_empty_keyword(self):
        assert _escape_like("") == ""

    def test_none_raises(self):
        # None 输入显式失败（调用方应保证非 None）
        with pytest.raises((TypeError, AttributeError)):
            _escape_like(None)
