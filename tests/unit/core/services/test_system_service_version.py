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


@pytest.mark.unit
class TestVersionPyprojectDiscovery:
    """_version_from_pyproject 真实路径查找（回归 off-by-one）。

    src-layout 下 version.py 位于 src/ginkgo/libs/utils/，pyproject.toml 在
    repo root（第 5 层）。原实现固定遍历 4 层够不到 root，永远返 None；
    改 while 循环向上查找后应命中。本测试不 mock，走真实文件系统查找。
    """

    def test_finds_real_pyproject_at_repo_root(self):
        """真实路径：_version_from_pyproject 应向上命中 repo root pyproject.toml。

        回归锚点：off-by-one 时此断言失败（返 None）。
        """
        from ginkgo.libs.utils.version import _version_from_pyproject

        result = _version_from_pyproject()
        assert result is not None, "未找到 repo root pyproject.toml（向上查找层数不足？off-by-one）"
        assert "." in result, f"版本非 semver 形态: {result!r}"

    def test_real_version_matches_pyproject(self, monkeypatch):
        """隔离 metadata 后，get_version() 应回退到真实 pyproject 版本（非 fallback 常量）。"""
        import ginkgo.libs.utils.version as v

        # 强制 metadata 不可用（模拟生产镜像未装 dist），逼 fallback 走 pyproject 真实路径
        monkeypatch.setattr(v, "_version_from_metadata", lambda: None)
        result = get_version()
        assert result  # 非空
        assert result != v._FALLBACK_VERSION, (
            f"get_version() 退化到 fallback 常量 {v._FALLBACK_VERSION!r}，"
            "说明 _version_from_pyproject 未命中真实 pyproject（off-by-one?）"
        )
