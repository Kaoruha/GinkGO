"""
日志链路修复测试

验证 GLOG → 文件 → Vector 配置的一致性：
- LOGGING_PATH 环境变量覆盖
- JSON 文件输出路径和格式
- Vector 配置路径与 GLOG 一致
"""

import json
import os

import pytest

from ginkgo.libs.core.config import GinkgoConfig


@pytest.mark.unit
class TestLoggingPathEnvOverride:
    """验证 LOGGING_PATH 支持环境变量覆盖"""

    def test_env_variable_takes_priority(self):
        """GINKGO_LOGGING_PATH 环境变量优先于 config.yml"""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("GINKGO_LOGGING_PATH", "/custom/log/path")
            config = GinkgoConfig()
            assert config.LOGGING_PATH == "/custom/log/path"

    def test_config_yml_as_fallback(self):
        """没有环境变量时回退到 config.yml"""
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("GINKGO_LOGGING_PATH", raising=False)
            config = GinkgoConfig()
            # 应返回 config.yml 中的值或默认值
            path = config.LOGGING_PATH
            assert path is not None
            assert len(path) > 0

    def test_default_path_without_env(self):
        """没有环境变量时使用默认值（包含 .ginkgo/logs）"""
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("GINKGO_LOGGING_PATH", raising=False)
            config = GinkgoConfig()
            path = config.LOGGING_PATH
            assert ".ginkgo" in path or "logs" in path


# ---------------------------------------------------------------------------
# Helper: patch logger module-level variables to redirect file output
# ---------------------------------------------------------------------------
import ginkgo.libs.core.logger as _logger_mod


def _patch_logging_path(log_dir):
    """Return (original_path, original_file_on) for later restoration."""
    return _logger_mod.LOGGING_PATH, _logger_mod.LOGGING_FILE_ON


def _restore_logging_path(original_path, original_file_on):
    _logger_mod.LOGGING_PATH = original_path
    _logger_mod.LOGGING_FILE_ON = original_file_on


@pytest.mark.unit
class TestJsonFileOutput:
    """验证 GLOG JSON 文件输出路径和格式"""

    def test_json_file_written_to_logging_path(self, tmp_path):
        """GLOG 实际写入 LOGGING_PATH 指定的目录"""
        log_dir = str(tmp_path / "logs")
        os.makedirs(log_dir, exist_ok=True)

        orig_path, orig_file_on = _patch_logging_path(log_dir)
        _logger_mod.LOGGING_PATH = log_dir
        _logger_mod.LOGGING_FILE_ON = True
        try:
            from ginkgo.libs.core.logger import GinkgoLogger

            logger = GinkgoLogger(
                "test_path_check",
                file_names=["test_pipeline"],
                console_log=False,
            )

            logger.INFO("pipeline test message")

            # flush handlers
            for h in logger.file_handlers:
                h.flush()

            # 验证文件被创建在 log_dir 下
            log_files = os.listdir(log_dir)
            assert any("test_pipeline" in f for f in log_files), \
                f"Expected log file in {log_dir}, found: {log_files}"

            # 清理
            for h in logger.file_handlers:
                h.close()
                logger.logger.removeHandler(h)
        finally:
            _restore_logging_path(orig_path, orig_file_on)

    def test_json_format_required_fields(self, tmp_path):
        """JSON 行包含必需字段：timestamp, level, message, trace_id"""
        log_dir = str(tmp_path / "logs")
        os.makedirs(log_dir, exist_ok=True)

        orig_path, orig_file_on = _patch_logging_path(log_dir)
        _logger_mod.LOGGING_PATH = log_dir
        _logger_mod.LOGGING_FILE_ON = True
        try:
            from ginkgo.libs.core.logger import GinkgoLogger

            logger = GinkgoLogger(
                "test_format_check",
                file_names=["test_format"],
                console_log=False,
            )

            # 设置 trace_id（实例方法）
            token = logger.set_trace_id("trace-123")

            logger.INFO("format test message")

            for h in logger.file_handlers:
                h.flush()

            # 清理 trace_id
            logger.clear_trace_id(token)

            # 读取日志文件并解析 JSON
            log_file = os.path.join(log_dir, "test_format.log")
            with open(log_file, "r") as f:
                lines = f.readlines()

            assert len(lines) >= 1, "No log lines written"
            parsed = json.loads(lines[-1])

            # 验证必需字段
            assert "timestamp" in parsed
            assert "level" in parsed
            assert "message" in parsed
            assert parsed["message"] == "format test message"
            assert "trace_id" in parsed
            assert parsed["trace_id"] == "trace-123"

            # 清理
            for h in logger.file_handlers:
                h.close()
                logger.logger.removeHandler(h)
        finally:
            _restore_logging_path(orig_path, orig_file_on)


@pytest.mark.unit
class TestLogCategoryRouting:
    """验证 log_category 字段用于 Vector 路由"""

    def test_backtest_category_in_json(self, tmp_path):
        """GLOG backtest 输出 log_category=backtest"""
        log_dir = str(tmp_path / "logs")
        os.makedirs(log_dir, exist_ok=True)

        orig_path, orig_file_on = _patch_logging_path(log_dir)
        _logger_mod.LOGGING_PATH = log_dir
        _logger_mod.LOGGING_FILE_ON = True
        try:
            from ginkgo.libs.core.logger import GinkgoLogger

            logger = GinkgoLogger(
                "test_category_check",
                file_names=["test_category"],
                console_log=False,
            )

            logger.set_log_category("backtest")
            logger.INFO("backtest event")
            for h in logger.file_handlers:
                h.flush()

            log_file = os.path.join(log_dir, "test_category.log")
            with open(log_file, "r") as f:
                lines = f.readlines()

            parsed = json.loads(lines[-1])
            assert parsed.get("log_category") == "backtest"

            # 清理
            for h in logger.file_handlers:
                h.close()
                logger.logger.removeHandler(h)
        finally:
            _restore_logging_path(orig_path, orig_file_on)


@pytest.mark.unit
class TestVectorConfigPathMatch:
    """验证 Vector 配置路径与 GLOG 使用同一变量"""

    def test_vector_includes_env_var(self):
        """vector.toml 的 include 路径使用 ${GINKGO_LOGGING_PATH}"""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        toml_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "deploy", "vector", "vector.toml"
        ))

        if not os.path.exists(toml_path):
            pytest.skip("vector.toml not found")

        with open(toml_path, "rb") as f:
            config = tomllib.load(f)

        includes = config["sources"]["ginkgo_logs"]["include"]
        assert len(includes) > 0, "No include patterns in vector.toml"

        # 验证路径引用了 GINKGO_LOGGING_PATH 环境变量
        assert any("${GINKGO_LOGGING_PATH}" in inc for inc in includes), \
            f"Expected ${{GINKGO_LOGGING_PATH}} in include patterns, got: {includes}"
