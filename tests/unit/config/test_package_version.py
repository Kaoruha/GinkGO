"""
CLI/API 版本真相源契约测试（#5406 AC#3）。

验证 ``ginkgo version`` CLI 与 ``GET /system/status`` 返回一致版本。

架构约束（订正：原论据 setup.py 循环已失效，真约束如下）：
  - ``config/package.py`` 被 CLI 快速路径（``main.py``）通过 ``sys.path.insert +
    import package`` 提升为**顶层裸模块**导入，**绕过** ``ginkgo/__init__.py``
    的 ServiceHub 重型加载。故 ``package.py`` 不能写任何 ``from ginkgo...``，
    只能 import 同目录 sibling ``_version_core``。
  - ``libs/utils/version.py`` 走运行时路径（``SystemService``），无此约束。
  - 两端共享 ``config/_version_core.py::resolve_version`` 算法收敛。
  - ``setup.py`` 现为空壳，setuptools 直接读 ``pyproject.toml``，**不**读
    ``package.py``；故打包循环不再是约束。
"""

import sys
from pathlib import Path

import pytest

from ginkgo.config.package import VERSION as PACKAGE_VERSION
from ginkgo.libs.utils.version import get_version


@pytest.mark.unit
class TestPackageVersionSource:
    """package.VERSION 必须与 API get_version() 同源（#5406 AC#3）。"""

    def test_package_version_equals_api_version(self):
        """CLI package.VERSION == API get_version()。

        重构后两端委托同一 resolve_version()，此断言近乎同义反复，
        但保留作 smoke：守护导入链（双模 shim / 委托）未断。
        """
        assert PACKAGE_VERSION == get_version(), (
            f"CLI {PACKAGE_VERSION!r} ≠ API {get_version()!r}，#5406 AC#3 违反"
        )

    def test_package_version_nonempty(self):
        """VERSION 非空、非占位符。"""
        assert PACKAGE_VERSION
        assert PACKAGE_VERSION != "unknown"
        assert PACKAGE_VERSION != "0.0.0+unknown"

    def test_package_version_matches_pyproject(self):
        """两端都应解析到 pyproject.toml 的真实版本（当前 0.8.x），非兜底常量。

        强制 exercise 真实解析路径，而非偶然命中兜底。
        """
        repo_root = Path(__file__).resolve().parents[3]
        pyproject = repo_root / "pyproject.toml"
        try:
            import tomllib
            with open(pyproject, "rb") as f:
                expected = tomllib.load(f).get("project", {}).get("version")
        except Exception:
            pytest.skip("无法解析 pyproject.toml")
        assert expected, "pyproject.toml 缺 [project].version"
        assert PACKAGE_VERSION == expected
        assert get_version() == expected

    def test_package_importable_via_src_prefix(self):
        """setup_install.py 契约：`from src.ginkgo.config.package import VERSION` 可用。

        setup_install.py:10 在 install 阶段（pip uninstall 前后）从源码读 VERSION
        命名构建产物（ginkgo-{VERSION}.tar.gz）。此时 ginkgo 可能尚未装/已卸载，
        importlib.metadata 失败，resolver 必须回退读源码 pyproject.toml。

        此导入路径要求 package.py 的 shim 第二分支用**相对导入**（`from
        ._version_core`）而非绝对（`from ginkgo.config._version_core`）——后者
        依赖 `ginkgo` 顶层可导入，违背 install 时"读源码不依赖已装包"原则。
        相对导入锚定 package.py 自身位置，src.ginkgo.config.* / ginkgo.config.*
        两种前缀都能定位到同目录源码文件。
        """
        import importlib
        # repo root 已在 sys.path（pytest rootdir），src 为 namespace package
        mod = importlib.import_module("src.ginkgo.config.package")
        assert mod.VERSION == PACKAGE_VERSION, (
            f"src.ginkgo.config.package.VERSION={mod.VERSION!r} ≠ "
            f"常规 PACKAGE_VERSION={PACKAGE_VERSION!r}，相对导入 shim 失效"
        )
        assert mod.VERSION != "0.0.0+unknown", "install 时 resolver 退化到兜底常量"

    def test_install_time_reads_source_when_metadata_fails(self):
        """install 时 ginkgo 未装（metadata 失败）→ resolver 必须读源码 pyproject。

        回归锚点：setup_install.py 在 pip uninstall ginkgo 后仍能拿到正确版本
        命名 sdist。若 resolver 仅依赖 importlib.metadata，install 时会得到
        兜底常量 `0.0.0+unknown` → pip install ginkgo-0.0.0+unknown.tar.gz 失败。
        """
        import ginkgo.config._version_core as core
        # 模拟 ginkgo 未装：metadata 路径返 None
        original = core._version_from_metadata
        core._version_from_metadata = lambda: None
        try:
            result = core.resolve_version()
        finally:
            core._version_from_metadata = original
        assert result == PACKAGE_VERSION, (
            f"metadata 失败时 resolve_version()={result!r}，应回退读源码得 "
            f"{PACKAGE_VERSION!r}（install 时命名 sdist 依赖此路径）"
        )

    def test_package_importable_as_top_level_module(self):
        """CLI 快速路径契约：package.py 能作为顶层裸模块 `import package` 导入。

        复刻 main.py:197-209 的 sys.path 技巧 —— 这要求 package.py 不能写任何
        `from ginkgo...` 导入（否则 ginkgo 未在快速路径 sys.path 上 → ImportError，
        或触发 ServiceHub 拖慢启动）。双模 shim 的第一分支（`from _version_core
        import resolve_version`）必须在此模式命中。
        """
        repo_root = Path(__file__).resolve().parents[3]
        config_dir = str(repo_root / "src" / "ginkgo" / "config")
        saved_path = list(sys.path)
        # 清掉可能已作为 ginkgo.config.* 缓存的副本，强制走顶层裸模块路径
        for mod in list(sys.modules):
            if mod in ("package", "_version_core") or mod.startswith("ginkgo.config._version_core"):
                # 注意：不删 ginkgo.config.package（其它测试可能依赖）
                if mod in ("package", "_version_core"):
                    del sys.modules[mod]

        sys.path.insert(0, config_dir)
        try:
            import package  # 顶层裸模块，与 main.py 快速路径一致
            assert package.VERSION == PACKAGE_VERSION, (
                f"快速路径 package.VERSION={package.VERSION!r} ≠ "
                f"常规 PACKAGE_VERSION={PACKAGE_VERSION!r}，双模 shim 失效"
            )
            assert package.PACKAGENAME == "ginkgo"
        finally:
            sys.path[:] = saved_path
            sys.modules.pop("package", None)
            sys.modules.pop("_version_core", None)

    def test_version_core_logs_when_metadata_lookup_fails(self, caplog):
        """metadata 查询失败时必须 emit debug log（#6518/#6486 可观测性不变量）。

        回归锚点：``_version_core`` 的 except 块用 ``return None`` 形态（非 ``pass``），
        绕过 ``test_except_pass_logging`` 守门扫描器（该扫描器只抓 ``except...: pass``
        形态）。故 logging 行为须由本测试直接断言，否则未来有人删掉 logging 行
        无人发现 —— 这正是 refactor 搬迁时漏带语义不变量的事故温床（CLAUDE.md
        「归因纪律（防 #4652 类事故）」）。
        """
        import logging
        from unittest.mock import patch

        import ginkgo.config._version_core as core

        # GinkgoLogger (logger.py:434) 把上层 logger propagate=False，caplog 经
        # root 收不到；直接把 caplog.handler 挂到目标 logger 绕开传播链。
        target = logging.getLogger(core.__name__)
        target.addHandler(caplog.handler)
        caplog.set_level(logging.DEBUG, logger=core.__name__)
        try:
            with patch("importlib.metadata.version", side_effect=Exception("boom")):
                result = core._version_from_metadata()
        finally:
            target.removeHandler(caplog.handler)
        assert result is None, "metadata 失败应返 None 触发 fallback"
        debug_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("importlib.metadata" in m for m in debug_msgs), (
            f"metadata 失败应留 debug 日志，实际 caplog: {debug_msgs}"
        )

    def test_version_core_logs_when_pyproject_parse_fails(self, caplog):
        """pyproject 解析失败时必须 emit debug log（同上，pyproject 路径对称）。"""
        import logging
        from unittest.mock import MagicMock, patch

        import ginkgo.config._version_core as core

        # tomllib.load 抛错 → except 块触发；walk 仍找到 repo root 的真 pyproject
        fake_tomllib = MagicMock()
        fake_tomllib.load.side_effect = Exception("parse boom")
        target = logging.getLogger(core.__name__)
        target.addHandler(caplog.handler)
        caplog.set_level(logging.DEBUG, logger=core.__name__)
        try:
            with patch.object(core, "tomllib", fake_tomllib):
                result = core._version_from_pyproject()
        finally:
            target.removeHandler(caplog.handler)
        assert result is None, "pyproject 解析失败应返 None 触发 fallback"
        debug_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("pyproject.toml" in m for m in debug_msgs), (
            f"pyproject 解析失败应留 debug 日志，实际 caplog: {debug_msgs}"
        )
