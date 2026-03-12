# Upstream: ServiceHub (通过 services.logging.level_service 访问), CLI commands
# Downstream: GLOG (日志记录器), GCONF (配置管理)
# Role: LevelService 动态日志级别管理服务 - 运行时调整日志级别，无需重启服务

from typing import Dict, List, Optional
import logging

from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import GLOG, GCONF


class LevelService(BaseService):
    """
    动态日志级别管理服务

    提供运行时日志级别调整功能，支持：
    - 按模块设置日志级别
    - 白名单验证（仅允许特定模块动态调整）
    - 重置为配置文件默认值

    Attributes:
        glog: GLOG 日志记录器实例
        _custom_levels: 自定义级别缓存 {module_name: level}
        _whitelist: 模块白名单
    """

    # 有效的日志级别
    VALID_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    def __init__(self, glog=None):
        """
        初始化 LevelService

        Args:
            glog: GLOG 实例（可选，默认使用全局 GLOG）
        """
        super().__init__(glog=glog)

        self._glog = glog if glog else GLOG
        self._custom_levels: Dict[str, str] = {}
        self._whitelist: List[str] = self._load_whitelist()

    def _load_whitelist(self) -> List[str]:
        """
        从 GCONF 加载模块白名单

        Returns:
            List[str]: 允许动态调整日志级别的模块列表
        """
        whitelist = getattr(GCONF, 'LOGGING_LEVEL_WHITELIST', ["backtest", "trading", "data", "analysis"])
        return whitelist if isinstance(whitelist, list) else []

    def set_level(self, module_name: str, level: str) -> ServiceResult:
        """
        设置指定模块的日志级别

        Args:
            module_name: 模块名称（必须在白名单中）
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)

        Returns:
            ServiceResult: 操作结果

        Raises:
            ValueError: 模块不在白名单或级别无效
        """
        # 验证模块在白名单中
        if module_name not in self._whitelist:
            raise ValueError(
                f"模块 '{module_name}' 不在白名单中。允许的模块: {', '.join(self._whitelist)}"
            )

        # 验证级别有效
        level_upper = level.upper()
        if level_upper not in self.VALID_LEVELS:
            raise ValueError(
                f"无效的日志级别: {level}。有效级别: {', '.join(self.VALID_LEVELS.keys())}"
            )

        # 设置自定义级别
        self._custom_levels[module_name] = level_upper

        # 应用到 GLOG（如果有 set_level 方法）
        if hasattr(self._glog, 'set_level'):
            try:
                # GinkgoLogger 支持按 handler 设置级别
                self._glog.set_level(level_upper)
            except Exception as e:
                self._logger.WARNING(f"设置日志级别失败: {e}")

        self._logger.INFO(f"模块 '{module_name}' 日志级别设置为 {level_upper}")

        return ServiceResult.success(
            data={"module": module_name, "level": level_upper},
            message=f"模块 '{module_name}' 日志级别已设置为 {level_upper}"
        )

    def get_level(self, module_name: str) -> str:
        """
        获取指定模块的当前日志级别

        Args:
            module_name: 模块名称

        Returns:
            str: 当前日志级别（自定义值或默认 INFO）
        """
        return self._custom_levels.get(module_name, "INFO")

    def get_all_levels(self) -> Dict[str, str]:
        """
        获取所有模块的当前日志级别

        Returns:
            Dict[str, str]: {module_name: level} 映射
        """
        result = {}
        for module in self._whitelist:
            result[module] = self.get_level(module)
        return result

    def reset_levels(self) -> ServiceResult:
        """
        重置所有模块为配置文件默认值

        清除所有自定义级别设置。

        Returns:
            ServiceResult: 操作结果
        """
        cleared_count = len(self._custom_levels)
        self._custom_levels.clear()

        self._logger.INFO(f"已重置 {cleared_count} 个模块的日志级别为默认值")

        return ServiceResult.success(
            data={"cleared_count": cleared_count},
            message=f"已重置 {cleared_count} 个模块的日志级别"
        )

    def get_whitelist(self) -> List[str]:
        """
        获取当前模块白名单

        Returns:
            List[str]: 白名单模块列表
        """
        return self._whitelist.copy()

    def is_module_allowed(self, module_name: str) -> bool:
        """
        检查模块是否允许动态调整级别

        Args:
            module_name: 模块名称

        Returns:
            bool: 是否在白名单中
        """
        return module_name in self._whitelist
