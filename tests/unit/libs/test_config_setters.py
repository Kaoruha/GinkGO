"""
TDD tests for GinkgoConfig setters (#5931).

config list 列出 5 个 key，但 quiet/log_path/working_path 无法 config set：
- quiet: GinkgoConfig 缺 set_quiet（真实调用 AttributeError；现有 CLI 测试用
  MagicMock 掩盖了此 bug，见 feedback_magicmock_method_attr_mask）
- log_path/working_path: set_logging_path/set_work_path 已存在，但 config_cli
  从未接线（命名漂移）

本文件用【真实 GinkgoConfig + tmp config.yml】测 setter 落盘行为，不 mock，
直击 set_quiet 缺失的真实 bug。
"""

import os

import pytest
import yaml


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """指向 tmp 的真实 config.yml + 新建 GinkgoConfig 单例。

    set_GINKGO_DIR=tmp_path 使 setting_path=tmp_path/config.yml；
    预置 '{}' 因 _write_config 先 open('r') 读现有内容。
    """
    config_file = tmp_path / "config.yml"
    config_file.write_text("{}\n")
    monkeypatch.setenv("GINKGO_DIR", str(tmp_path))

    from ginkgo.libs.core.config import GinkgoConfig

    if hasattr(GinkgoConfig, "_instance"):
        del GinkgoConfig._instance
    cfg = GinkgoConfig()
    return cfg, config_file


# ---------------------------------------------------------------------------
# set_quiet（#5931 核心：方法此前完全缺失）
# ---------------------------------------------------------------------------


class TestSetQuiet:
    """set_quiet 须持久化到 config.yml 并同步 env（仿 set_python_path）。"""

    def test_set_quiet_true_persists_to_config_yml(self, tmp_config):
        cfg, config_file = tmp_config
        cfg.set_quiet(True)
        data = yaml.safe_load(config_file.read_text())
        assert data["quiet"] is True

    def test_set_quiet_false_persists_to_config_yml(self, tmp_config):
        cfg, config_file = tmp_config
        cfg.set_quiet(False)
        data = yaml.safe_load(config_file.read_text())
        assert data["quiet"] is False

    def test_set_quiet_updates_env(self, tmp_config, monkeypatch):
        monkeypatch.delenv("GINKGO_QUIET", raising=False)
        cfg, _ = tmp_config
        cfg.set_quiet(True)
        assert os.environ["GINKGO_QUIET"] == "True"

    def test_set_quiet_non_bool_no_write(self, tmp_config):
        """非 bool 入参不落盘（isinstance 守卫，对称 set_cpu_ratio/set_python_path）。"""
        cfg, config_file = tmp_config
        cfg.set_quiet("yes")  # type: ignore[arg-type]
        data = yaml.safe_load(config_file.read_text())
        assert "quiet" not in data
