"""
版本读取契约测试。

验证 get_version() 的 fallback 链与 SystemService.VERSION 的单一真相源行为。
通过公共接口 + mock 注入固定 fallback 各分支。

注：算法实现共享自 ``ginkgo.config._version_core``（``version.py`` 仅薄壳委托），
故 fallback 链 mock 注入点为 ``ginkgo.config._version_core._version_from_*``。
patch 必须作用在 ``resolve_version`` 实际查符号的命名空间（``_version_core``），
否则 patch 命中调用方命名空间、被测函数看不到 → 假阳性。
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
        with patch("ginkgo.config._version_core._version_from_metadata", return_value=None):
            with patch(
                "ginkgo.config._version_core._version_from_pyproject",
                return_value="0.8.2",
            ):
                assert get_version() == "0.8.2"

    def test_prefers_metadata_when_available(self):
        """importlib.metadata 可用时，优先返回 dist 版本（不被 pyproject 覆盖）。"""
        with patch(
            "ginkgo.config._version_core._version_from_metadata",
            return_value="1.2.3",
        ):
            with patch(
                "ginkgo.config._version_core._version_from_pyproject",
                return_value="0.8.2",
            ):
                assert get_version() == "1.2.3"

    def test_returns_fallback_when_all_sources_fail(self):
        """所有来源都读不到时，返回兜底常量，永不抛异常。"""
        with patch("ginkgo.config._version_core._version_from_metadata", return_value=None):
            with patch(
                "ginkgo.config._version_core._version_from_pyproject",
                return_value=None,
            ):
                result = get_version()
                assert isinstance(result, str)
                assert result  # 非空


@pytest.mark.unit
class TestVersionPyprojectDiscovery:
    """_version_from_pyproject 真实路径查找（回归 off-by-one）。

    _version_core.py 位于 src/ginkgo/config/，pyproject.toml 在 repo root
    （向上 3 层 dirname）。原 off-by-one 实现固定遍历 4 层在旧位置（libs/utils/，
    5 层）永远返 None；改 while 循环向上查找后应命中。本测试不 mock，走真实
    文件系统查找 —— 守护任意未来"固定层数"回退。
    """

    def test_finds_real_pyproject_at_repo_root(self):
        """真实路径：_version_from_pyproject 应向上命中 repo root pyproject.toml。

        回归锚点：off-by-one 时此断言失败（返 None）。
        """
        from ginkgo.config._version_core import _version_from_pyproject

        result = _version_from_pyproject()
        assert result is not None, "未找到 repo root pyproject.toml（向上查找层数不足？off-by-one）"
        assert "." in result, f"版本非 semver 形态: {result!r}"

    def test_real_version_matches_pyproject(self, monkeypatch):
        """隔离 metadata 后，get_version() 应回退到真实 pyproject 版本（非 fallback 常量）。"""
        import ginkgo.config._version_core as core

        # 强制 metadata 不可用（模拟生产镜像未装 dist），逼 fallback 走 pyproject 真实路径
        monkeypatch.setattr(core, "_version_from_metadata", lambda: None)
        result = get_version()
        assert result  # 非空
        assert result != core._FALLBACK_VERSION, (
            f"get_version() 退化到 fallback 常量 {core._FALLBACK_VERSION!r}，"
            "说明 _version_from_pyproject 未命中真实 pyproject（off-by-one?）"
        )
