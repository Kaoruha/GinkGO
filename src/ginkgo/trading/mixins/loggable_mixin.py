"""
日志管理Mixin

提供统一的日志管理功能
"""

from typing import List


class LoggableMixin:
    """日志管理Mixin，提供统一的日志管理功能"""

    def __init__(self, loggers=[], **kwargs):
        """初始化日志管理"""
        self.loggers = loggers
        # 默认添加GLOG（如果还没有的话）
        try:
            from ginkgo.libs import GLOG
            self.add_logger(GLOG)
        except ImportError:
            # 如果GLOG不可用，继续但不添加默认日志器
            pass
        super().__init__(**kwargs)

    def add_logger(self, logger) -> None:
        """
        添加日志器

        Args:
            logger: 要添加的日志器
        """
        if logger in self.loggers:
            return
        self.loggers.append(logger)

    def reset_logger(self) -> None:
        """重置日志器列表"""
        self.loggers = []

    def log(self, level: str, msg: str, *args, **kwargs) -> None:
        """
        统一日志接口

        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            msg: 日志消息
            *args: 额外参数
            **kwargs: 额外关键字参数
        """
        level_up = level.upper()
        if level_up == "DEBUG":
            for logger in self.loggers:
                if hasattr(logger, "DEBUG"):
                    logger.DEBUG(msg)
        elif level_up == "INFO":
            for logger in self.loggers:
                if hasattr(logger, "INFO"):
                    logger.INFO(msg)
        elif level_up == "WARNING":
            for logger in self.loggers:
                if hasattr(logger, "WARN"):
                    logger.WARN(msg)
        elif level_up == "ERROR":
            for logger in self.loggers:
                if hasattr(logger, "ERROR"):
                    logger.ERROR(msg)
        elif level_up == "CRITICAL":
            for logger in self.loggers:
                if hasattr(logger, "CRITICAL"):
                    logger.CRITICAL(msg)
        else:
            # 对于未知级别，尝试直接调用
            for logger in self.loggers:
                if hasattr(logger, level_up):
                    getattr(logger, level_up)(msg)