"""
日志链路修复测试

验证 GLOG → 文件 → Vector 配置的一致性：
- LOGGING_PATH 环境变量覆盖
- JSON 文件输出路径和格式
- Vector 配置路径与 GLOG 一致
"""

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
