"""
TDD tests for #6465: 诊断日志与 CLI 业务输出分流。

Unix 约定：诊断信息走 stderr，命令业务结果（如 `-r` 的纯 JSON）走 stdout。
历史问题：`[GCONF]` 裸 print、GLOG 的 RichHandler、`time_logger` 的 `⚡ FUNCTION`
都默认写 stdout，污染 `ginkgo ... -r` 的机器可读输出，导致 jq/json.tool 解析失败。

每条用例对应一处根因，通过公共接口验证「诊断在 stderr、stdout 干净」的行为契约。
"""

import os
import re

import pytest


@pytest.fixture(autouse=True)
def _reset_config_singleton():
    """每个用例给 GinkgoConfig 单例一个干净起点。"""
    from ginkgo.libs.core.config import GinkgoConfig

    if hasattr(GinkgoConfig, "_instance"):
        del GinkgoConfig._instance
    yield
    if hasattr(GinkgoConfig, "_instance"):
        del GinkgoConfig._instance


# ---------------------------------------------------------------------------
# 根因 A: config.py 的 [GCONF] 诊断 print 默认写 stdout
# ---------------------------------------------------------------------------


class TestGconfLogsToStderr:
    """`[GCONF]` 配置缓存/复制诊断必须写 stderr，不得污染 stdout。"""

    def test_config_cache_update_goes_to_stderr(self, tmp_path, monkeypatch, capsys):
        """
        配置缓存刷新时打印的 `[GCONF] Config cache updated` 必须落在 stderr。
        复现 #6465：此前裸 print() 写 stdout，污染 `data get -r`。
        """
        import yaml

        from ginkgo.libs.core.config import GinkgoConfig

        # 指向一个真实存在的临时 config.yml，使 setting_path 可读
        conf_dir = tmp_path / "ginkgo"
        conf_dir.mkdir()
        (conf_dir / "config.yml").write_text(
            yaml.safe_dump({"logging": {"level": "info"}}), encoding="utf-8"
        )
        monkeypatch.setenv("GINKGO_DIR", str(conf_dir))

        cfg = GinkgoConfig()
        # 强制缓存失效 → 触发重读 + print
        cfg._has_local_config = True
        cfg._config_cache = {}
        cfg._config_mtime = 0

        cfg._read_config()

        captured = capsys.readouterr()
        # 诊断不得污染 stdout
        assert "[GCONF]" not in captured.out
        # 诊断应可见于 stderr
        assert "[GCONF] Config cache updated" in captured.err

    def test_secure_cache_update_goes_to_stderr(self, tmp_path, monkeypatch, capsys):
        """secure 缓存刷新诊断同样必须落在 stderr。"""
        import yaml

        from ginkgo.libs.core.config import GinkgoConfig

        conf_dir = tmp_path / "ginkgo"
        conf_dir.mkdir()
        (conf_dir / "secure.yml").write_text(
            yaml.safe_dump({"key": "val"}), encoding="utf-8"
        )
        monkeypatch.setenv("GINKGO_DIR", str(conf_dir))

        cfg = GinkgoConfig()
        cfg._has_local_secure = True
        cfg._secure_cache = {}
        cfg._secure_mtime = 0

        cfg._read_secure()

        captured = capsys.readouterr()
        assert "[GCONF]" not in captured.out
        assert "[GCONF] Secure cache updated" in captured.err


# ---------------------------------------------------------------------------
# 根因 B: logger.py 的 RichHandler 默认写 stdout（本 rich 版本实测）
# ---------------------------------------------------------------------------


class TestGlogConsoleToStderr:
    """GLOG 控制台 RichHandler 必须写 stderr，INFO/WARN/ERROR 不得污染 stdout。

    用 capfd（fd 级捕获）而非 capsys：Rich Console 在构造时缓存 sys.stderr
    引用，fd 级捕获才能可靠抓到 RichHandler 输出。
    """

    def test_info_console_goes_to_stderr(self, capfd):
        """GLOG.INFO 经 RichHandler 应落在 stderr。"""
        from ginkgo.libs.core.logger import GinkgoLogger

        logger = GinkgoLogger("test_stderr_info_6465", console_log=True)
        # 短 marker：Rich RichHandler 会把"marker + 调用方源码定位"按 80 列折行并把
        # 路径塞回 marker 中间，长 marker 必被切碎。短 marker 单行可整段渲染。
        marker = "M6465I"
        logger.INFO(marker)

        captured = capfd.readouterr()
        # Rich RichHandler 会把长日志行（marker + 源码定位）按捕获终端 80 列折行，
        # 把 marker 从中间断开。行为契约是「marker 到达 stderr、stdout 干净」，
        # 故剥离空白后再判成员关系，不受 Rich 折行影响。
        out_norm = re.sub(r"\s+", "", captured.out)
        err_norm = re.sub(r"\s+", "", captured.err)
        assert marker not in out_norm
        assert marker in err_norm

    def test_warn_console_goes_to_stderr(self, capfd):
        """GLOG.WARN 经 RichHandler 应落在 stderr。"""
        from ginkgo.libs.core.logger import GinkgoLogger

        logger = GinkgoLogger("test_stderr_warn_6465", console_log=True)
        marker = "M6465W"
        logger.WARN(marker)

        captured = capfd.readouterr()
        # Rich RichHandler 会把长日志行（marker + 源码定位）按捕获终端 80 列折行，
        # 把 marker 从中间断开。行为契约是「marker 到达 stderr、stdout 干净」，
        # 故剥离空白后再判成员关系，不受 Rich 折行影响。
        out_norm = re.sub(r"\s+", "", captured.out)
        err_norm = re.sub(r"\s+", "", captured.err)
        assert marker not in out_norm
        assert marker in err_norm


# ---------------------------------------------------------------------------
# 根因 C: common.py 的 time_logger/retry 用模块级共享 console（默认 stdout）
# 打印 ⚡ FUNCTION / Retry FUNCTION 性能诊断，污染 -r 纯 JSON
# ---------------------------------------------------------------------------


class TestTimeLoggerDiagnosticToStderr:
    """time_logger 的 `⚡ FUNCTION ... executed in` 诊断必须走 stderr。

    复现 #6465：模块级共享 `console = Console()` 默认写 stdout，time_logger
    在慢函数上打印的 `⚡ FUNCTION` 落到 stdout，污染 `data get -r` 的纯 JSON。
    """

    def test_function_executed_goes_to_stderr(self, capfd):
        """被装饰慢函数的 FUNCTION 执行耗时诊断应落在 stderr。"""
        from ginkgo.libs.utils.common import time_logger

        # enabled=True 强制监控、threshold=-1 保证任意耗时都越过阈值触发打印
        @time_logger(enabled=True, threshold=-1)
        def slow_op():
            return 42

        slow_op()

        captured = capfd.readouterr()
        assert "FUNCTION" not in captured.out
        assert "FUNCTION" in captured.err

