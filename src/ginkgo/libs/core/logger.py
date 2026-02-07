# Upstream: All Modules
# Downstream: Standard Library
# Role: GLOG日志核心提供统一日志记录和格式化输出功能支持Rich控制台输出和文件日志记录支持交易系统功能和组件集成提供完整业务支持






from typing import List
import os
import inspect
import logging
import threading
import hashlib
import time
import re
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from pathlib import Path
from ginkgo.libs.core.config import GCONF

# Read Configure
LOGGING_LEVEL_CONSOLE = GCONF.LOGGING_LEVEL_CONSOLE
LOGGING_LEVEL_FILE = GCONF.LOGGING_LEVEL_FILE
LOGGING_COLOR = GCONF.LOGGING_COLOR
LOGGING_PATH = GCONF.LOGGING_PATH
LOGGING_DEFAULT_FILE = GCONF.LOGGING_DEFAULT_FILE
LOGGING_FILE_ON = GCONF.LOGGING_FILE_ON


class GinkgoLogger:
    """
    Args:
        logger_name(str): logger name
        file_names(List): file names
        console_log(bool): if turn on console
    Return:
        None
    """

    def __init__(self, logger_name: str, file_names: List = None, console_log=False):
        self.logger_name = logger_name
        self.backup_count = 3
        self.max_file_bytes = 2 * 1024 * 1024 * 1024
        self._file_names = file_names
        self.file_handlers = []
        self._console_handler_name = "ginkgo_console_logger"
        self.file_formatter = logging.Formatter(
            fmt="[%(asctime)s][%(levelname)s]:%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.console_formatter = logging.Formatter(
            "P:%(process)d %(message)s",
            datefmt="%m-%d %H:%M",
        )

        if not os.path.exists(LOGGING_PATH):
            Path(LOGGING_PATH).mkdir(parents=True, exist_ok=True)
            print(f"Create folder {LOGGING_PATH}")

        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        # 错误追踪相关的实例变量
        self._error_patterns = {}  # 错误模式计数 {pattern_hash: count}
        self._error_timestamps = {}  # 错误时间戳 {pattern_hash: last_log_time}
        self._error_lock = threading.RLock()  # 线程安全锁
        self._max_error_history = 1000  # 最大错误历史记录数

        self._setup_handlers(console_log)

    def _setup_handlers(self, console_log):
        # 文件日志已禁用 - 仅保留控制台输出
        # self._setup_file_handler()
        self._setup_console_handler(console_log)
        # self._setup_error_handler()

    def _should_log_error(self, msg: str) -> tuple[bool, str]:
        """
        智能流量控制：判断是否应该记录错误日志
        
        Args:
            msg: 错误消息
            
        Returns:
            tuple[bool, str]: (是否应该记录, 处理后的消息)
        """
        # 生成错误模式哈希（基于消息的前100个字符，忽略动态参数）
        pattern_msg = msg[:100] if len(msg) > 100 else msg
        # 移除常见的动态部分（数字、时间戳等）来生成模式
        pattern_msg = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', pattern_msg)  # 日期
        pattern_msg = re.sub(r'\d{2}:\d{2}:\d{2}', 'TIME', pattern_msg)  # 时间
        pattern_msg = re.sub(r'\b\d+\b', 'NUM', pattern_msg)  # 数字
        pattern_hash = hashlib.md5(pattern_msg.encode()).hexdigest()[:8]
        
        current_time = time.time()
        
        with self._error_lock:
            # 获取当前模式的计数
            count = self._error_patterns.get(pattern_hash, 0) + 1
            self._error_patterns[pattern_hash] = count
            self._error_timestamps[pattern_hash] = current_time
            
            # 清理过期的错误记录（保留最近的记录）
            if len(self._error_patterns) > self._max_error_history:
                # 删除最旧的100个记录
                sorted_items = sorted(
                    self._error_timestamps.items(), 
                    key=lambda x: x[1]
                )
                for old_hash, _ in sorted_items[:100]:
                    self._error_patterns.pop(old_hash, None)
                    self._error_timestamps.pop(old_hash, None)
            
            # 智能频率控制逻辑
            if count == 1:
                # 首次出现，完整记录
                return True, f"🔥 [{pattern_hash}] {msg}"
            elif count <= 5:
                # 少量重复，简化记录
                return True, f"⚠️ [{pattern_hash}] {msg} ({count}th occurrence)"
            elif count == 10:
                # 达到阈值，发出警告
                return True, f"🚨 [{pattern_hash}] Error pattern occurred {count} times, consider investigation: {msg}"
            elif count % 50 == 0:
                # 每50次记录一次统计信息
                return True, f"📊 [{pattern_hash}] Error pattern count: {count} - {msg}"
            else:
                # 高频错误，不记录
                return False, msg

    def get_error_stats(self) -> dict:
        """获取错误统计信息"""
        with self._error_lock:
            total_patterns = len(self._error_patterns)
            top_errors = sorted(
                self._error_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return {
                "total_error_patterns": total_patterns,
                "top_error_patterns": [
                    {"pattern_hash": pattern, "count": count}
                    for pattern, count in top_errors
                ],
                "total_error_count": sum(self._error_patterns.values())
            }
    
    def clear_error_stats(self):
        """清除错误统计"""
        with self._error_lock:
            self._error_patterns.clear()
            self._error_timestamps.clear()

    def _setup_file_handler(self):
        if not self._file_names:
            self._file_names = [LOGGING_DEFAULT_FILE]
        for i in self._file_names:
            handler = self.add_file_handler(i, LOGGING_LEVEL_FILE)
            self.file_handlers.append(handler)

    def gen_file_handler_name(self, file_name) -> str:
        return f"file_handler_{file_name}"

    def remove_file_handler(self, handler_name: str) -> None:
        for handler in self.logger.handlers:
            if handler.name == self.gen_file_handler_name(handler_name):
                self.logger.removeHandler(handler)

    def add_file_handler(self, file_name: str, level: str) -> None:
        if not file_name.endswith(".log"):
            file_name += ".log"
        # 删除同名文件处理器
        self.remove_file_handler(file_name)

        # 添加新的文件处理器
        file_path = os.path.join(LOGGING_PATH, file_name)
        file_handler = RotatingFileHandler(
            filename=file_path,
            encoding="utf-8",
            mode="a",
            maxBytes=self.max_file_bytes,
            backupCount=self.backup_count,
        )
        file_handler.set_name(self.gen_file_handler_name(file_name))
        file_handler.setLevel(self.get_log_level(level))
        file_handler.setFormatter(self.file_formatter)
        self.file_handlers.append(file_handler)
        self.logger.addHandler(file_handler)
        return file_handler

    def _setup_console_handler(self, console_log):
        self.console_handler = RichHandler(
            show_time=True,
            omit_repeated_times=False,
            rich_tracebacks=True,
            log_time_format="[%X]",
        )
        self.console_handler.set_name(self._console_handler_name)
        self.console_handler.setLevel(self.get_log_level(LOGGING_LEVEL_CONSOLE))
        self.console_handler.setFormatter(self.console_formatter)

        if console_log:
            self.logger.addHandler(self.console_handler)

    def _setup_error_handler(self):
        error_path = os.path.join(LOGGING_PATH, "error.log")
        error_handler = RotatingFileHandler(
            filename=error_path,
            encoding="utf-8",
            mode="a",
            maxBytes=self.max_file_bytes,
            backupCount=self.backup_count,
        )
        error_handler.set_name("ginkgo_error")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.file_formatter)
        self.logger.addHandler(error_handler)

    def reset_logfile(self, file_name: str) -> None:
        [self.logger.removeHandler(i) for i in self.file_handlers]
        if not LOGGING_FILE_ON:
            return
        self._file_names = []
        self._file_names.append(file_name)
        self._setup_file_handler()

    def set_level(self, level: str, handler_type: str = 'all') -> None:
        """设置日志级别，支持指定handler类型
        
        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            handler_type: handler类型 ('all', 'console', 'file', 'error')
        """
        level_int = self.get_log_level(level)
        
        if handler_type == 'all':
            self.logger.setLevel(level_int)
            if hasattr(self, 'console_handler'):
                self.console_handler.setLevel(level_int)
            for handler in self.file_handlers:
                handler.setLevel(level_int)
        elif handler_type == 'console':
            self.set_console_level(level)
        elif handler_type == 'file':
            self.set_file_level(level)
        elif handler_type == 'error':
            self.set_error_level(level)

    def set_console_level(self, level: str):
        """单独设置控制台日志级别"""
        if hasattr(self, 'console_handler'):
            self.console_handler.setLevel(self.get_log_level(level))

    def set_file_level(self, level: str):
        """设置所有文件日志级别"""
        level_int = self.get_log_level(level)
        for handler in self.file_handlers:
            handler.setLevel(level_int)

    def set_error_level(self, level: str):
        """设置错误日志级别"""
        for handler in self.logger.handlers:
            if handler.name == 'ginkgo_error':
                handler.setLevel(self.get_log_level(level))
                break

    def get_log_level(self, level: str) -> int:
        return logging.getLevelName(level.upper())

    def get_current_levels(self) -> dict:
        """获取当前所有Handler的日志级别"""
        levels = {
            'logger': logging.getLevelName(self.logger.level),
            'handlers': {}
        }
        
        for handler in self.logger.handlers:
            handler_name = handler.name or str(type(handler).__name__)
            levels['handlers'][handler_name] = logging.getLevelName(handler.level)
        
        return levels

    def log(self, level, msg: str):
        caller = inspect.stack()[2]
        function = caller.function
        filename = caller.filename.split("/")[-1]
        lineno = caller.lineno
        log_method = getattr(self.logger, level.lower())
        # log_method(f"{msg}  [{filename} -> {function}()  L:{lineno}]", stacklevel=2)
        log_method(msg, stacklevel=4)

    def DEBUG(self, msg: str):
        if not self.logger.isEnabledFor(logging.DEBUG):
            return
        self.log("DEBUG", msg)

    def INFO(self, msg: str):
        if not self.logger.isEnabledFor(logging.INFO):
            return
        self.log("INFO", msg)

    def WARN(self, msg: str):
        if not self.logger.isEnabledFor(logging.WARNING):
            return
        self.log("WARNING", msg)

    def ERROR(self, msg: str):
        if not self.logger.isEnabledFor(logging.ERROR):
            return
        
        # 使用智能流量控制
        should_log, processed_msg = self._should_log_error(msg)
        if should_log:
            self.log("ERROR", processed_msg)

    def CRITICAL(self, msg: str):
        if not self.logger.isEnabledFor(logging.CRITICAL):
            return
        self.log("CRITICAL", msg)
