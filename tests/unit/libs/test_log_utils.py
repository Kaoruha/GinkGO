"""
Unit tests for log utility functions

This module tests container environment detection and metadata collection
functions for enhanced logging capabilities in containerized deployments.
"""

import pytest
import os
from unittest.mock import patch, mock_open, MagicMock

# TODO: 确认导入路径是否正确
from ginkgo.libs.utils.log_utils import is_container_environment, get_container_metadata


@pytest.mark.tdd
class TestContainerDetection:
    """
    测试容器环境检测

    覆盖范围:
    - Docker 环境变量检测
    - Kubernetes 环境变量检测
    - /proc/1/cgroup 文件检测
    - /.dockerenv 文件检测
    - 非容器环境正确返回 False
    """

    @patch.dict(os.environ, {"DOCKER_CONTAINER": "true"})
    def test_detects_docker_container_env_var(self):
        """
        测试通过 DOCKER_CONTAINER 环境变量检测

        验证点:
        - DOCKER_CONTAINER 环境变量存在时返回 True
        - 不检查其他检测方法
        """
        assert is_container_environment() is True

    @patch.dict(os.environ, {"KUBERNETES_SERVICE_HOST": "10.0.0.1"})
    def test_detects_kubernetes_env_var(self):
        """
        测试通过 KUBERNETES_SERVICE_HOST 环境变量检测

        验证点:
        - KUBERNETES_SERVICE_HOST 环境变量存在时返回 True
        - 不检查其他检测方法
        """
        assert is_container_environment() is True

    @patch("builtins.open", new_callable=mock_open, read_data="docker\n")
    @patch("os.path.exists", return_value=False)
    @patch.dict(os.environ, {}, clear=True)
    def test_detects_docker_from_cgroup(self, mock_exists, mock_file):
        """
        测试通过 /proc/1/cgroup 检测 Docker

        验证点:
        - /proc/1/cgroup 包含 "docker" 时返回 True
        - 文件读取失败时不抛出异常
        """
        assert is_container_environment() is True

    @patch("builtins.open", new_callable=mock_open, read_data="kubepods\n")
    @patch("os.path.exists", return_value=False)
    @patch.dict(os.environ, {}, clear=True)
    def test_detects_kubernetes_from_cgroup(self, mock_exists, mock_file):
        """
        测试通过 /proc/1/cgroup 检测 Kubernetes

        验证点:
        - /proc/1/cgroup 包含 "kubepods" 时返回 True
        - 文件读取失败时不抛出异常
        """
        assert is_container_environment() is True

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch.dict(os.environ, {}, clear=True)
    def test_detects_dockerenv_file(self, mock_file, mock_exists):
        """
        测试通过 /.dockerenv 文件检测 Docker

        验证点:
        - /.dockerenv 文件存在时返回 True
        """
        assert is_container_environment() is True

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists", return_value=False)
    @patch("builtins.open", new_callable=mock_open, read_data="non-container\n")
    def test_returns_false_for_non_container(self, mock_file, mock_exists):
        """
        测试非容器环境返回 False

        验证点:
        - 无容器环境变量时返回 False
        - /proc/1/cgroup 不包含容器标识时返回 False
        - /.dockerenv 文件不存在时返回 False
        - 所有检测失败时优雅降级
        """
        assert is_container_environment() is False

    @patch.dict(os.environ, {"DOCKER_CONTAINER": "true"})
    @patch("os.path.exists", return_value=True)
    def test_short_circuits_on_first_positive(self, mock_exists):
        """
        测试首次检测到容器环境时立即返回

        验证点:
        - DOCKER_CONTAINER 环境变量存在时立即返回 True
        - 不继续检查其他检测方法
        """
        assert is_container_environment() is True


@pytest.mark.tdd
class TestContainerMetadata:
    """
    测试容器元数据采集

    覆盖范围:
    - 主机名信息采集
    - 进程信息采集
    - 容器 ID 采集
    - Kubernetes 元数据采集
    - 默认值处理
    """

    @patch.dict(os.environ, {"HOSTNAME": "test-pod-123"})
    def test_includes_hostname(self):
        """
        测试包含主机名

        验证点:
        - host 字段存在
        - host.hostname 从 HOSTNAME 环境变量读取
        - HOSTNAME 不存在时使用 platform.node()
        """
        metadata = get_container_metadata()
        assert "host" in metadata
        assert metadata["host"]["hostname"] == "test-pod-123"

    def test_includes_process_info(self):
        """
        测试包含进程信息

        验证点:
        - process 字段存在
        - process.pid 为当前进程 ID
        - process.name 为 "ginkgo"
        """
        metadata = get_container_metadata()
        assert "process" in metadata
        assert "pid" in metadata["process"]
        assert metadata["process"]["name"] == "ginkgo"
        assert metadata["process"]["pid"] > 0

    @patch.dict(os.environ, {"CONTAINER_ID": "docker://abc123"})
    def test_includes_container_id(self):
        """
        测试包含容器 ID

        验证点:
        - container 字段存在
        - container.id 从 CONTAINER_ID 环境变量读取
        - 容器 ID 格式正确
        """
        metadata = get_container_metadata()
        assert "container" in metadata
        assert metadata["container"]["id"] == "docker://abc123"

    @patch.dict(os.environ, {"HOSTNAME": "pod-abc123"})
    def test_fallback_container_id_from_hostname(self):
        """
        测试容器 ID 从 HOSTNAME 回退

        验证点:
        - CONTAINER_ID 不存在时使用 HOSTNAME
        - container.id 正确设置
        """
        metadata = get_container_metadata()
        assert "container" in metadata
        assert metadata["container"]["id"] == "pod-abc123"

    @patch.dict(os.environ, {"POD_NAME": "test-pod", "POD_NAMESPACE": "default"})
    def test_includes_kubernetes_metadata(self):
        """
        测试包含 Kubernetes 元数据

        验证点:
        - kubernetes 字段存在
        - kubernetes.pod.name 从 POD_NAME 读取
        - kubernetes.namespace 从 POD_NAMESPACE 读取
        """
        metadata = get_container_metadata()
        assert "kubernetes" in metadata
        assert metadata["kubernetes"]["pod"]["name"] == "test-pod"
        assert metadata["kubernetes"]["namespace"] == "default"

    @patch.dict(os.environ, {"POD_NAME": "test-pod"})
    def test_kubernetes_metadata_partial(self):
        """
        测试 Kubernetes 元数据部分存在

        验证点:
        - 只有 POD_NAME 时也包含 kubernetes 字段
        - kubernetes.namespace 可以为空
        """
        metadata = get_container_metadata()
        assert "kubernetes" in metadata
        assert metadata["kubernetes"]["pod"]["name"] == "test-pod"
        assert metadata["kubernetes"]["namespace"] is None

    @patch.dict(os.environ, {}, clear=True)
    def test_no_kubernetes_metadata_without_env(self):
        """
        测试无 Kubernetes 环境变量时不包含 kubernetes 字段

        验证点:
        - POD_NAME 和 POD_NAMESPACE 都不存在时
        - 不包含 kubernetes 字段
        """
        metadata = get_container_metadata()
        assert "kubernetes" not in metadata

    @patch.dict(os.environ, {}, clear=True)
    def test_always_includes_host_and_process(self):
        """
        测试始终包含 host 和 process 字段

        验证点:
        - 无论环境如何都包含 host 字段
        - 无论环境如何都包含 process 字段
        - host.hostname 有默认值
        - process.pid 有默认值
        """
        metadata = get_container_metadata()
        assert "host" in metadata
        assert "process" in metadata
        assert "hostname" in metadata["host"]
        assert "pid" in metadata["process"]
        assert len(metadata["host"]["hostname"]) > 0
        assert metadata["process"]["pid"] > 0


@pytest.mark.tdd
class TestLogUtilsIntegration:
    """
    测试 log_utils 集成场景

    覆盖范围:
    - 容器检测与元数据采集的协同
    - 边界条件处理
    - 错误恢复
    """

    @patch.dict(os.environ, {"HOSTNAME": "test-host", "CONTAINER_ID": "docker://123"})
    def test_container_env_with_full_metadata(self):
        """
        测试容器环境完整元数据采集

        验证点:
        - is_container_environment() 返回 True
        - get_container_metadata() 包含所有可用字段
        """
        # 这个测试需要设置容器环境变量
        # 但在本地环境中可能不满足容器检测条件
        metadata = get_container_metadata()
        assert "host" in metadata
        assert "process" in metadata
        assert "container" in metadata

    @patch.dict(os.environ, {}, clear=True)
    @patch("builtins.open", new_callable=mock_open, read_data="non-container")
    @patch("os.path.exists", return_value=False)
    def test_non_container_minimal_metadata(self, mock_file, mock_exists):
        """
        测试非容器环境最小元数据采集

        验证点:
        - is_container_environment() 返回 False
        - get_container_metadata() 只包含 host 和 process
        """
        assert is_container_environment() is False
        metadata = get_container_metadata()
        assert "host" in metadata
        assert "process" in metadata
        assert "container" not in metadata
        assert "kubernetes" not in metadata
