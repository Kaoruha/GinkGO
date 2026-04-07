# Upstream: libs顶层模块(__init__.py)、core容器
# Downstream: GinkgoConfig(配置), GinkgoLogger(日志)
# Role: 核心工具包入口，导出GinkgoConfig配置管理和GinkgoLogger日志类，GinkgoThreadManager通过顶层延迟加载






"""
Core library components for Ginkgo.

This module provides core functionality including configuration management,
logging, and threading utilities.
"""

from ginkgo.libs.core.config import GinkgoConfig
from ginkgo.libs.core.logger import GinkgoLogger

# GinkgoThreadManager 通过 ginkgo.libs 顶层导入（依赖 GLOG，需延迟加载）
# from ginkgo.libs.core.threading import GinkgoThreadManager

__all__ = ["GinkgoConfig", "GinkgoLogger", "GinkgoThreadManager"]
