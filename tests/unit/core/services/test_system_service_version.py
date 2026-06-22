"""
版本读取契约测试。

验证 get_version() 的 fallback 链与 SystemService.VERSION 的单一真相源行为。
通过公共接口 + mock 注入固定 fallback 各分支，不耦合内部解析实现。
"""

import pytest
from unittest.mock import patch

from ginkgo.libs.utils.version import get_version
from ginkgo.core.services.system_service import SystemService


@pytest.mark.unit
class TestSystemServiceVersionSource:
    """SystemService.VERSION 必须来自 get_version() 单一真相源。"""

    def test_version_equals_get_version(self):
        """VERSION 与 get_version() 一致（非独立硬编码）。"""
        assert SystemService.VERSION == get_version()

    def test_version_not_hardcoded_unknown(self):
        """VERSION 不再是 unknown 占位符。"""
        assert SystemService.VERSION != "unknown"
        assert SystemService.VERSION  # 非空


@pytest.mark.unit
class TestVersionFallbackChain:
    """get_version() fallback 链契约。"""

    def test_falls_back_to_pyproject_when_importlib_fails(self):
        """importlib.metadata 不可用时，fallback 读 pyproject.toml 返回有效版本。"""
        with patch("ginkgo.libs.utils.version._version_from_metadata", return_value=None):
            with patch(
                "ginkgo.libs.utils.version._version_from_pyproject",
                return_value="0.8.2",
            ):
                assert get_version() == "0.8.2"

    def test_prefers_metadata_when_available(self):
        """importlib.metadata 可用时，优先返回 dist 版本（不被 pyproject 覆盖）。"""
        with patch(
            "ginkgo.libs.utils.version._version_from_metadata",
            return_value="1.2.3",
        ):
            with patch(
                "ginkgo.libs.utils.version._version_from_pyproject",
                return_value="0.8.2",
            ):
                assert get_version() == "1.2.3"

    def test_returns_fallback_when_all_sources_fail(self):
        """所有来源都读不到时，返回兜底常量，永不抛异常。"""
        with patch("ginkgo.libs.utils.version._version_from_metadata", return_value=None):
            with patch(
                "ginkgo.libs.utils.version._version_from_pyproject",
                return_value=None,
            ):
                result = get_version()
                assert isinstance(result, str)
                assert result  # 非空
