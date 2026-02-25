"""
Log utilities module for Ginkgo library

Provides container environment detection and metadata collection functions
for enhanced logging capabilities in containerized deployments.
"""

import os
import platform


def is_container_environment() -> bool:
    """
    检测当前是否运行在容器环境中

    Returns:
        bool: 如果运行在容器环境中返回True，否则返回False

    检测方法:
        1. 检查环境变量 (DOCKER_CONTAINER, KUBERNETES_SERVICE_HOST)
        2. 检查 /proc/1/cgroup 文件内容
        3. 检查 /.dockerenv 文件是否存在
    """
    # 1. 检查环境变量
    if os.getenv("DOCKER_CONTAINER"):
        return True
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return True

    # 2. 检查 /proc/1/cgroup 文件
    try:
        with open("/proc/1/cgroup") as f:
            content = f.read()
            if "docker" in content or "kubepods" in content:
                return True
    except (FileNotFoundError, PermissionError, IOError):
        pass

    # 3. 检查 /.dockerenv 文件
    return os.path.exists("/.dockerenv")


def get_container_metadata() -> dict:
    """
    采集容器元数据

    Returns:
        dict: 包含容器相关元数据的字典，包括:
            - host: 主机名信息
            - container: 容器ID (如果可用)
            - kubernetes: Kubernetes元数据 (如果可用)
            - process: 进程信息
    """
    metadata = {
        "host": {"hostname": os.getenv("HOSTNAME", platform.node())},
        "process": {"pid": os.getpid(), "name": "ginkgo"}
    }

    # 容器ID
    container_id = os.getenv("CONTAINER_ID") or os.getenv("HOSTNAME")
    if container_id:
        metadata["container"] = {"id": container_id}

    # Kubernetes 元数据
    pod_name = os.getenv("POD_NAME")
    namespace = os.getenv("POD_NAMESPACE")
    if pod_name or namespace:
        metadata["kubernetes"] = {
            "pod": {"name": pod_name} if pod_name else {},
            "namespace": namespace
        }

    return metadata
