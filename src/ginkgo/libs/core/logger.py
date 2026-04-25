# Upstream: 全局所有模块 (通过GLOG单例记录日志)
# Downstream: structlog, contextvars(分布式追踪trace_id/span_id), Number/to_decimal(类型支持), datetime
# Role: GinkgoLogger结构化日志核心，基于structlog实现JSON/Rich双输出，支持trace_id/span_id分布式追踪和业务上下文绑定


# Imports for structlog and distributed logging
import contextvars
import contextlib
import platform
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List, Union

# 导入 Number 类型用于类型提示
from ginkgo.libs.data.number import Number, to_decimal


# ==================== T029: 创建 contextvars.ContextVar ====================

_trace_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)

# T064: span_id 用于分布式追踪中的子操作
_span_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "span_id", default=None
)

# 业务上下文 context variables
_log_category_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "log_category", default=None
)
_business_context_ctx: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "business_context", default={}
)






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

# ==================== T006-T008: 日志核心枚举类型 ====================


class LogMode(str, Enum):
    """
    日志模式枚举 (T006)

    用于控制系统日志输出行为：
    - container: 容器模式，输出JSON格式日志到stdout/stderr
    - local: 本地模式，输出到文件和控制台
    - auto: 自动检测，根据运行环境自动选择
    """
    CONTAINER = "container"
    LOCAL = "local"
    AUTO = "auto"


class LogCategory(str, Enum):
    """
    日志类别枚举 (T007)

    用于区分不同业务场景的日志：
    - system: 系统级别日志
    - backtest: 回测相关日志
    """
    SYSTEM = "system"
    BACKTEST = "backtest"


class LogLevel(str, Enum):
    """
    日志级别枚举 (T008)

    ECS标准日志级别：
    - debug: 调试信息
    - info: 一般信息
    - warning: 警告信息
    - error: 错误信息
    - critical: 严重错误
    """
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ==================== T009-T012: structlog 处理器 ====================


def ecs_processor(logger, log_method, event_dict):
    """
    ECS 字段映射处理器 (T009)

    将标准日志字段映射到 Elastic Common Schema (ECS) 格式：
    - @timestamp: ISO 8601格式时间戳
    - log.level: 日志级别
    - log.logger: 日志记录器名称
    - message: 日志消息
    - process.pid: 进程ID
    - host.hostname: 主机名
    - trace.id: 追踪ID (T034)

    Args:
        logger: structlog logger对象
        log_method: 日志方法
        event_dict: 日志事件字典

    Returns:
        Dict: 更新后的日志事件字典
    """
    # 时间戳映射
    event_dict["@timestamp"] = event_dict.pop("timestamp", datetime.utcnow().isoformat())

    # log.* 字段映射
    event_dict["log"] = {
        "level": event_dict.pop("level", "info"),
        "logger": event_dict.pop("logger_name", "ginkgo")
    }

    # 消息字段
    event_dict["message"] = event_dict.pop("event", "")

    # 进程和主机信息（仅在不存在时设置，避免覆盖 container_metadata_processor 的值）
    if "process" not in event_dict:
        event_dict["process"] = {"pid": os.getpid()}
    if "host" not in event_dict:
        event_dict["host"] = {"hostname": os.getenv("HOSTNAME", platform.node())}

    # T034: 添加 trace_id
    trace_id = _trace_id_ctx.get()
    if trace_id:
        event_dict["trace"] = {"id": trace_id}

    # T064: 添加 span_id
    span_id = _span_id_ctx.get()
    if span_id:
        if "trace" not in event_dict:
            event_dict["trace"] = {}
        event_dict["trace"]["span_id"] = span_id

    return event_dict


def ginkgo_processor(logger, log_method, event_dict):
    """
    Ginkgo 业务字段处理器 (T010)

    注入Ginkgo业务相关的扩展字段：
    - ginkgo.log_category: 日志类别
    - ginkgo.strategy_id: 策略ID
    - ginkgo.portfolio_id: 组合ID
    - ginkgo.event_type: 事件类型
    - ginkgo.symbol: 交易标的

    Args:
        logger: structlog logger对象
        log_method: 日志方法
        event_dict: 日志事件字典

    Returns:
        Dict: 更新后的日志事件字典
    """
    if "ginkgo" not in event_dict:
        event_dict["ginkgo"] = {}

    # 从 contextvars 获取业务上下文
    log_category = _log_category_ctx.get()
    if log_category:
        event_dict["ginkgo"]["log_category"] = log_category

    # 获取所有绑定的业务上下文
    business_context = _business_context_ctx.get()
    for key, value in business_context.items():
        event_dict["ginkgo"][key] = value

    return event_dict


def container_metadata_processor(logger, log_method, event_dict):
    """
    容器元数据处理器 (T011)

    在容器环境中注入容器和Kubernetes元数据：
    - container.id: 容器ID
    - kubernetes.pod.name: Pod名称
    - kubernetes.namespace: 命名空间

    Args:
        logger: structlog logger对象
        log_method: 日志方法
        event_dict: 日志事件字典

    Returns:
        Dict: 更新后的日志事件字典
    """
    try:
        from ginkgo.libs.utils.log_utils import get_container_metadata
        metadata = get_container_metadata()
        if "container" in metadata:
            event_dict["container"] = metadata["container"]
        if "kubernetes" in metadata:
            event_dict["kubernetes"] = metadata["kubernetes"]
        # 确保 host 和 process 字段存在
        if "host" in metadata:
            event_dict["host"] = metadata["host"]
        if "process" in metadata:
            event_dict["process"] = metadata["process"]
    except ImportError:
        pass

    return event_dict


def masking_processor(logger, log_method, event_dict):
    """
    敏感数据脱敏处理器 (T012)

    根据 GCONF.LOGGING_MASK_FIELDS 配置对敏感字段进行脱敏处理。

    Args:
        logger: structlog logger对象
        log_method: 日志方法
        event_dict: 日志事件字典

    Returns:
        Dict: 更新后的日志事件字典
    """
    # TODO: 在 T005 任务中实现 GCONF.LOGGING_MASK_FIELDS 配置
    mask_fields = []
    if hasattr(GCONF, "LOGGING_MASK_FIELDS"):
        mask_fields = GCONF.LOGGING_MASK_FIELDS

    for field in mask_fields:
        if field in event_dict:
            event_dict[field] = "***MASKED***"

    return event_dict


# ==================== T013: structlog 配置 ====================


def configure_structlog():
    """
    配置 structlog (T013, T055)

    设置完整的处理器链（按性能优化排序）：

    === 快速处理器（无 I/O，简单操作）===
    1. contextvars.merge_contextvars - 合并上下文变量
    2. stdlib.add_log_level - 添加日志级别
    3. stdlib.add_logger_name - 添加日志记录器名称
    4. UnicodeDecoder - Unicode解码

    === 快速处理器（简单逻辑）===
    5. ginkgo_processor - Ginkgo业务字段（简单字典检查）
    6. masking_processor - 敏感数据脱敏（字段迭代）

    === 中等处理器（格式化/重组）===
    7. TimeStamper - 添加时间戳（日期时间格式化）
    8. ecs_processor - ECS字段映射（字典重组）

    === 慢速处理器（I/O 或复杂处理）===
    9. container_metadata_processor - 容器元数据（可能触发文件 I/O）
    10. StackInfoRenderer - 渲染堆栈信息（堆栈遍历）
    11. format_exc_info - 格式化异常信息（异常处理）

    === 最慢处理器（放在最后）===
    12. JSONRenderer - JSON渲染器（JSON 序列化）

    Performance Notes (T055):
    - cache_logger_on_first_use=True: 首次调用后缓存 logger 实例，提升 10-20%
    - 处理器按性能排序：快速处理器在前，减少不必要的数据处理
    - JSONRenderer 放在最后：仅在最终输出时才进行序列化

    Args:
        None

    Returns:
        None
    """
    try:
        import structlog

        structlog.configure(
            processors=[
                # === 快速处理器（极快）===
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.UnicodeDecoder(),
                # === 快速处理器（简单逻辑）===
                ginkgo_processor,
                masking_processor,
                # === 中等处理器（格式化）===
                structlog.processors.TimeStamper(fmt="iso"),
                ecs_processor,
                # === 慢速处理器（可选）===
                container_metadata_processor,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                # === 最慢处理器（放在最后）===
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            # T055: 缓存 logger 实例以提升性能
            cache_logger_on_first_use=True,
        )
    except ImportError:
        # structlog 未安装，使用标准日志
        pass


# ==================== 原有配置读取 ====================

# Read Configure
LOGGING_LEVEL_CONSOLE = GCONF.LOGGING_LEVEL_CONSOLE
LOGGING_LEVEL_FILE = GCONF.LOGGING_LEVEL_FILE
LOGGING_COLOR = GCONF.LOGGING_COLOR
LOGGING_PATH = GCONF.LOGGING_PATH
LOGGING_DEFAULT_FILE = GCONF.LOGGING_DEFAULT_FILE
LOGGING_FILE_ON = GCONF.LOGGING_FILE_ON


class GinkgoLogger:
    """
    GinkgoLogger - 基于 structlog 的结构化日志记录器

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

        # T037: 检测日志模式
        mode = getattr(GCONF, 'LOGGING_MODE', 'auto')
        if mode == 'auto':
            from ginkgo.libs.utils.log_utils import is_container_environment
            self._is_container = is_container_environment()
        elif mode == 'container':
            self._is_container = True
        else:  # local
            self._is_container = False

        # 配置 structlog 和 handlers
        if self._is_container:
            # 容器模式：JSON 输出到 stdout/stderr
            configure_structlog()
        else:
            # 本地模式：Rich 控制台 + 文件
            # 在本地模式下仍然配置 structlog 用于业务逻辑
            configure_structlog()

        self._setup_handlers(console_log)

        # 初始化分组命名空间（简洁API）
        self.backtest = _BacktestLogNamespace(self)
        self.execution = _ExecutionLogNamespace(self)
        self.component = _ComponentLogNamespace(self)
        self.performance = _PerformanceLogNamespace(self)

    def _setup_handlers(self, console_log):
        # T037-T039: 文件日志支持
        # 文件日志统一使用 JSON 格式（供 Vector 采集）
        # stdout 可以根据模式选择格式
        if LOGGING_FILE_ON:
            # 始终使用 JSON 格式文件日志（容器和本地环境统一）
            self._setup_json_file_handler()
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

    def _setup_json_file_handler(self):
        """
        容器模式：设置 JSON 格式文件日志处理器

        输出到 /var/log/ginkgo/ 目录，使用 JSON 格式供 Vector 采集解析。
        """
        if not self._file_names:
            self._file_names = [LOGGING_DEFAULT_FILE]

        for file_name in self._file_names:
            if not file_name.endswith(".log"):
                file_name += ".log"

            # 容器模式使用 /var/log/ginkgo/ 路径
            file_path = os.path.join(LOGGING_PATH, file_name)

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 创建 JSON 格式化器
            import json

            class DecimalEncoder(json.JSONEncoder):
                """处理 Decimal 类型的 JSON 编码器"""
                def default(self, obj):
                    if isinstance(obj, Decimal):
                        return float(obj)
                    return super().default(obj)

            class JsonFormatter(logging.Formatter):
                """JSON 格式化器 - 输出单行 JSON 供 Vector 解析"""

                def format(self, record):
                    log_obj = {
                        "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                        "level": record.levelname.lower(),
                        "logger_name": record.name,
                        "message": record.getMessage(),
                        "pid": os.getpid(),
                        "hostname": platform.node(),
                    }

                    # 添加 trace_id (从 contextvars 获取)
                    trace_id = _trace_id_ctx.get(None)
                    if trace_id:
                        log_obj["trace_id"] = trace_id

                    # 添加 span_id
                    span_id = _span_id_ctx.get(None)
                    if span_id:
                        log_obj["span_id"] = span_id

                    # 添加 log_category
                    log_category = _log_category_ctx.get(None)
                    if log_category:
                        log_obj["log_category"] = log_category

                    # 添加业务上下文（转换 Decimal 为 float）
                    business_context = _business_context_ctx.get({})
                    if business_context:
                        for key, value in business_context.items():
                            if isinstance(value, Decimal):
                                log_obj[key] = float(value)
                            else:
                                log_obj[key] = value

                    # 异常信息
                    if record.exc_info:
                        log_obj["exception"] = self.formatException(record.exc_info)

                    return json.dumps(log_obj, ensure_ascii=False, cls=DecimalEncoder)

            # 创建文件处理器
            file_handler = RotatingFileHandler(
                filename=file_path,
                encoding="utf-8",
                mode="a",
                maxBytes=self.max_file_bytes,
                backupCount=self.backup_count,
            )
            file_handler.set_name(f"json_{self.gen_file_handler_name(file_name)}")
            file_handler.setLevel(self.get_log_level(LOGGING_LEVEL_FILE))
            file_handler.setFormatter(JsonFormatter())
            self.file_handlers.append(file_handler)
            self.logger.addHandler(file_handler)

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

    def DEBUG(self, msg: str) -> None:
        """记录 DEBUG 级别日志"""
        if not self.logger.isEnabledFor(logging.DEBUG):
            return

        # T116: 生产环境 DEBUG 日志采样（减少日志量）
        sampling_rate = getattr(GCONF, 'LOGGING_SAMPLING_RATE', 0.1)
        if sampling_rate < 1.0:
            import random
            if random.random() > sampling_rate:
                return  # 采样跳过此条日志

        # T037: 本地模式使用标准 logging 输出到文件，容器模式使用 structlog
        if not self._is_container:
            # 本地模式：使用标准 logging（支持文件输出）
            self.logger.debug(msg)
        else:
            # 容器模式：使用 structlog JSON 输出
            try:
                import structlog
                log = structlog.get_logger(self.logger_name)
                log.debug(msg)
            except ImportError:
                self.logger.debug(msg)

            # 同时写入文件（供 Vector 采集）
            self.logger.debug(msg)

    def INFO(self, msg: str) -> None:
        """记录 INFO 级别日志"""
        if not self.logger.isEnabledFor(logging.INFO):
            return

        # T037: 本地模式使用标准 logging 输出到文件，容器模式使用 structlog
        if not self._is_container:
            # 本地模式：使用标准 logging（支持文件输出）
            self.logger.info(msg)
        else:
            # 容器模式：使用 structlog JSON 输出到 stdout/stderr
            try:
                import structlog
                log = structlog.get_logger(self.logger_name)
                log.info(msg)
            except ImportError:
                self.logger.info(msg)

            # 同时写入文件（供 Vector 采集）
            self.logger.info(msg)

    def WARN(self, msg: str) -> None:
        """记录 WARNING 级别日志"""
        if not self.logger.isEnabledFor(logging.WARNING):
            return

        # T037: 本地模式使用标准 logging 输出到文件，容器模式使用 structlog
        if not self._is_container:
            # 本地模式：使用标准 logging（支持文件输出）
            self.logger.warning(msg)
        else:
            # 容器模式：使用 structlog JSON 输出
            try:
                import structlog
                log = structlog.get_logger(self.logger_name)
                log.warning(msg)
            except ImportError:
                self.logger.warning(msg)

            # 同时写入文件（供 Vector 采集）
            self.logger.warning(msg)

    def WARNING(self, msg: str) -> None:
        """记录 WARNING 级别日志（WARN 方法的别名）"""
        self.WARN(msg)

    def ERROR(self, msg: str) -> None:
        """记录 ERROR 级别日志（含智能流量控制）"""
        if not self.logger.isEnabledFor(logging.ERROR):
            return

        # 使用智能流量控制
        should_log, processed_msg = self._should_log_error(msg)
        if should_log:
            # T037: 本地模式使用标准 logging 输出到文件，容器模式使用 structlog
            if not self._is_container:
                # 本地模式：使用标准 logging（支持文件输出）
                self.logger.error(processed_msg)
            else:
                # 容器模式：使用 structlog JSON 输出
                try:
                    import structlog
                    log = structlog.get_logger(self.logger_name)
                    log.error(processed_msg)
                except ImportError:
                    self.logger.error(processed_msg)

                # 同时写入文件（供 Vector 采集）
                self.logger.error(processed_msg)

    def CRITICAL(self, msg: str) -> None:
        """记录 CRITICAL 级别日志"""
        if not self.logger.isEnabledFor(logging.CRITICAL):
            return

        # T037: 本地模式使用标准 logging 输出到文件，容器模式使用 structlog
        if not self._is_container:
            # 本地模式：使用标准 logging（支持文件输出）
            self.logger.critical(msg)
        else:
            # 容器模式：使用 structlog JSON 输出
            try:
                import structlog
                log = structlog.get_logger(self.logger_name)
                log.critical(msg)
            except ImportError:
                self.logger.critical(msg)

            # 同时写入文件（供 Vector 采集）
            self.logger.critical(msg)

    # ==================== T030-T033: trace_id 上下文管理 ====================

    def set_trace_id(self, trace_id: str) -> contextvars.Token:
        """
        设置当前 trace_id（使用 contextvars）(T030)

        Args:
            trace_id: 追踪ID字符串

        Returns:
            contextvars.Token: 用于恢复上下文的令牌
        """
        return _trace_id_ctx.set(trace_id)

    def get_trace_id(self) -> Optional[str]:
        """
        获取当前 trace_id (T031)

        Returns:
            Optional[str]: 当前追踪ID，如果未设置则返回 None
        """
        return _trace_id_ctx.get()

    def clear_trace_id(self, token: contextvars.Token) -> None:
        """
        清除 trace_id，恢复之前的值 (T032)

        Args:
            token: set_trace_id 返回的令牌
        """
        _trace_id_ctx.reset(token)

    @contextlib.contextmanager
    def with_trace_id(self, trace_id: str):
        """
        临时设置 trace_id 的上下文管理器 (T033)

        Args:
            trace_id: 临时追踪ID字符串

        Yields:
            None

        Example:
            >>> with logger.with_trace_id("trace-123"):
            ...     logger.INFO("This log has trace_id")
        """
        token = _trace_id_ctx.set(trace_id)
        try:
            yield
        finally:
            _trace_id_ctx.reset(token)

    # ==================== T064: span_id 上下文管理 ====================

    def set_span_id(self, span_id: str) -> contextvars.Token:
        """
        设置当前 span_id（用于分布式追踪中的子操作）

        Args:
            span_id: Span ID字符串

        Returns:
            contextvars.Token: 用于恢复上下文的令牌

        Example:
            >>> token = GLOG.set_span_id("span-456")
            >>> GLOG.INFO("Processing sub-operation")
            >>> GLOG.clear_span_id(token)
        """
        return _span_id_ctx.set(span_id)

    def get_span_id(self) -> Optional[str]:
        """
        获取当前 span_id

        Returns:
            Optional[str]: 当前Span ID，如果未设置则返回 None
        """
        return _span_id_ctx.get()

    def clear_span_id(self, token: contextvars.Token) -> None:
        """
        清除 span_id，恢复之前的值

        Args:
            token: set_span_id 返回的令牌
        """
        _span_id_ctx.reset(token)

    @contextlib.contextmanager
    def with_span_id(self, span_id: str):
        """
        临时设置 span_id 的上下文管理器

        Args:
            span_id: 临时Span ID字符串

        Yields:
            None

        Example:
            >>> with logger.with_span_id("span-456"):
            ...     logger.INFO("This log has both trace_id and span_id")
        """
        token = _span_id_ctx.set(span_id)
        try:
            yield
        finally:
            _span_id_ctx.reset(token)

    # ==================== 业务上下文管理 ====================

    def set_log_category(self, category: str) -> None:
        """
        设置日志类别

        Args:
            category: 日志类别 ("system" 或 "backtest")

        Example:
            >>> GLOG.set_log_category("backtest")
            >>> GLOG.INFO("Backtest started")  # 日志将包含 log_category="backtest"
        """
        _log_category_ctx.set(category)

    def bind_context(self, **kwargs) -> None:
        """
        绑定业务上下文（会自动添加到所有后续日志）

        Args:
            **kwargs: 业务上下文字段
                - strategy_id: UUID
                - portfolio_id: UUID
                - event_type: str
                - symbol: str
                - direction: str
                - 其他自定义字段

        Example:
            >>> GLOG.bind_context(
            ...     strategy_id=strategy.uuid,
            ...     portfolio_id=portfolio.uuid
            ... )
            >>> GLOG.INFO("Signal generated")  # 自动包含上述字段
        """
        current_context = _business_context_ctx.get()
        if current_context is None:
            current_context = {}
        current_context.update(kwargs)
        _business_context_ctx.set(current_context)

    def unbind_context(self, *keys: str) -> None:
        """
        解绑指定的上下文字段

        Args:
            *keys: 要解绑的字段名称

        Example:
            >>> GLOG.unbind_context("strategy_id", "portfolio_id")
        """
        current_context = _business_context_ctx.get()
        if current_context:
            for key in keys:
                current_context.pop(key, None)
            _business_context_ctx.set(current_context)

    def clear_context(self) -> None:
        """
        清除所有业务上下文

        Example:
            >>> GLOG.clear_context()
        """
        _business_context_ctx.set({})
        _log_category_ctx.set(None)

    # ==================== 内部辅助方法 ====================

    def _normalize_number(self, value: Union[Number, None]) -> Optional[float]:
        """
        统一数值类型为 float（用于 JSON 序列化）

        支持: float, int, Decimal
        返回: float 或 None
        """
        if value is None:
            return None
        if isinstance(value, float):
            return value
        if isinstance(value, (int, str)):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        return float(value)

    # ==================== 便捷方法：带字段提示的事件日志 ====================

    def log_signal_event(self, symbol: str, direction: str, **kwargs):
        """
        记录信号事件

        必需字段: symbol, direction
        可选字段: signal_volume, signal_reason, signal_weight, signal_confidence, strategy_id

        Example:
            >>> GLOG.log_signal_event(
            ...     symbol="000001.SZ",
            ...     direction="LONG",
            ...     signal_volume=1000,
            ...     signal_reason="MA金叉",
            ...     strategy_id=strategy.uuid
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="SIGNALGENERATION",
            symbol=symbol,
            direction=direction,
            **kwargs
        )
        self.INFO(f"Signal generated: {direction} {symbol}")

    def log_order_event(self, order_id: str, **kwargs):
        """
        记录订单事件

        必需字段: order_id
        可选字段: order_type, limit_price, frozen_money, symbol, direction

        Example:
            >>> GLOG.log_order_event(
            ...     order_id=order.uuid,
            ...     order_type="LIMIT",
            ...     limit_price=10.50,
            ...     symbol="000001.SZ",
            ...     direction="LONG"
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(event_type="ORDERSUBMITTED", order_id=order_id, **kwargs)
        self.INFO(f"Order submitted: {order_id}")

    def log_order_fill_event(self, order_id: str, price: Number, volume: int, **kwargs):
        """
        记录成交事件

        必需字段: order_id, transaction_price, transaction_volume
        可选字段: trade_id, commission, slippage

        Args:
            order_id: 订单ID
            price: 成交价格 (支持 float/int/Decimal)
            volume: 成交数量
            **kwargs: 其他字段，如 commission (支持 float/int/Decimal), slippage

        Example:
            >>> # 支持 float
            >>> GLOG.log_order_fill_event(
            ...     order_id=order.uuid,
            ...     price=10.52,
            ...     volume=1000,
            ...     commission=5.26
            ... )
            >>> # 支持 Decimal
            >>> GLOG.log_order_fill_event(
            ...     order_id=order.uuid,
            ...     price=Decimal("10.52"),
            ...     volume=1000,
            ...     commission=Decimal("5.26")
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="ORDERFILLED",
            order_id=order_id,
            transaction_price=price,
            transaction_volume=volume,
            **kwargs
        )
        self.INFO(f"Order filled: {order_id} @ {price} x{volume}")

    def log_position_event(self, symbol: str, volume: int, **kwargs):
        """
        记录持仓事件

        必需字段: position_code, position_volume
        可选字段: position_cost, position_price (支持 float/int/Decimal)

        Example:
            >>> GLOG.log_position_event(
            ...     symbol="000001.SZ",
            ...     volume=1000,
            ...     position_cost=10520.00  # 支持 float
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="POSITIONUPDATE",
            position_code=symbol,
            position_volume=volume,
            **kwargs
        )
        self.INFO(f"Position updated: {symbol} {volume} shares")

    def log_capital_event(self, total_value: Number, available_cash: Number, **kwargs):
        """
        记录资金事件

        必需字段: total_value, available_cash (支持 float/int/Decimal)
        可选字段: net_value, drawdown, pnl (支持 float/int/Decimal)

        Example:
            >>> # 支持 float
            >>> GLOG.log_capital_event(
            ...     total_value=100000.00,
            ...     available_cash=50000.00,
            ...     pnl=5000.00
            ... )
            >>> # 支持 Decimal
            >>> GLOG.log_capital_event(
            ...     total_value=Decimal("100000.00"),
            ...     available_cash=Decimal("50000.00"),
            ...     pnl=Decimal("5000.00")
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="CAPITALUPDATE",
            total_value=total_value,
            available_cash=available_cash,
            **kwargs
        )
        self.INFO(f"Capital updated: total={total_value}, cash={available_cash}")

    def log_risk_event(self, risk_type: str, risk_reason: str, **kwargs):
        """
        记录风控事件

        必需字段: risk_type, risk_reason
        可选字段: risk_limit_value, risk_actual_value (支持 float/int/Decimal)

        Example:
            >>> GLOG.log_risk_event(
            ...     risk_type="POSITION_LIMIT",
            ...     risk_reason="单股持仓超限",
            ...     risk_limit_value=0.2,  # 支持 float
            ...     risk_actual_value=0.25
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="RISKBREACH",
            risk_type=risk_type,
            risk_reason=risk_reason,
            **kwargs
        )
        self.WARN(f"Risk event: {risk_type} - {risk_reason}")

    def log_component_event(self, component_name: str, message: str, **kwargs):
        """
        记录组件日志

        必需字段: component_name
        可选字段: component_version, component_instance, module_name

        Example:
            >>> GLOG.log_component_event(
            ...     component_name="Strategy",
            ...     component_version="1.0.0",
            ...     message="策略初始化完成"
            ... )
        """
        self.set_log_category("component")
        self.bind_context(component_name=component_name, **kwargs)
        self.INFO(message)

    def log_performance_event(self, function_name: str, duration_ms: float, **kwargs):
        """
        记录性能日志

        必需字段: function_name, duration_ms
        可选字段: memory_mb, cpu_percent, throughput, module_name, call_site

        Example:
            >>> GLOG.log_performance_event(
            ...     function_name="calculate_signals",
            ...     duration_ms=125.5,
            ...     memory_mb=256.8,
            ...     module_name="ginkgo.trading.strategies"
            ... )
        """
        self.set_log_category("performance")
        self.bind_context(
            function_name=function_name,
            duration_ms=duration_ms,
            **kwargs
        )
        self.INFO(f"Performance: {function_name} took {duration_ms}ms")

    # ==================== 错误事件便捷方法 ====================

    def log_order_rejected_event(self, order_id: str, reject_code: str, reject_reason: str, **kwargs):
        """
        记录订单拒绝事件

        必需字段: order_id, reject_code, reject_reason
        可选字段: symbol, direction, limit_price

        Example:
            >>> GLOG.log_order_rejected_event(
            ...     order_id=order.uuid,
            ...     reject_code="INSUFFICIENT_FUNDS",
            ...     reject_reason="可用资金不足",
            ...     symbol="000001.SZ"
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="ORDERREJECTED",
            order_id=order_id,
            reject_code=reject_code,
            reject_reason=reject_reason,
            **kwargs
        )
        self.ERROR(f"Order rejected: {order_id} - {reject_code}: {reject_reason}")

    def log_order_cancelled_event(self, order_id: str, cancel_reason: str, **kwargs):
        """
        记录订单取消事件

        必需字段: order_id, cancel_reason
        可选字段: cancelled_quantity

        Example:
            >>> GLOG.log_order_cancelled_event(
            ...     order_id=order.uuid,
            ...     cancel_reason="用户取消",
            ...     cancelled_quantity=500
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="ORDERCANCELACK",
            order_id=order_id,
            cancel_reason=cancel_reason,
            **kwargs
        )
        self.WARN(f"Order cancelled: {order_id} - {cancel_reason}")

    def log_order_ack_event(self, order_id: str, broker_order_id: str, **kwargs):
        """
        记录订单确认事件（实盘交易）

        必需字段: order_id, broker_order_id
        可选字段: symbol, direction, limit_price, ack_message, order_status

        Example:
            >>> GLOG.log_order_ack_event(
            ...     order_id=order.uuid,
            ...     broker_order_id="broker-12345",
            ...     symbol="000001.SZ",
            ...     order_status="ACCEPTED"
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="ORDERACK",
            order_id=order_id,
            broker_order_id=broker_order_id,
            **kwargs
        )
        self.INFO(f"Order acknowledged: {order_id} -> {broker_order_id}")

    def log_order_expired_event(self, order_id: str, expire_reason: str, **kwargs):
        """
        记录订单过期事件

        必需字段: order_id, expire_reason
        可选字段: expired_quantity

        Example:
            >>> GLOG.log_order_expired_event(
            ...     order_id=order.uuid,
            ...     expire_reason="订单有效期已过",
            ...     expired_quantity=1000
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="ORDEREXPIRED",
            order_id=order_id,
            expire_reason=expire_reason,
            **kwargs
        )
        self.WARN(f"Order expired: {order_id} - {expire_reason}")

    def log_execution_rejected_event(self, tracking_id: str, reject_reason: str, **kwargs):
        """
        记录执行拒绝事件（实盘交易）

        必需字段: tracking_id, reject_reason
        可选字段: symbol, expected_volume, reject_code

        Example:
            >>> GLOG.log_execution_rejected_event(
            ...     tracking_id="track-123",
            ...     reject_reason="券商拒绝订单",
            ...     symbol="000001.SZ"
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="EXECUTIONREJECTION",
            tracking_id=tracking_id,
            reject_reason=reject_reason,
            **kwargs
        )
        self.ERROR(f"Execution rejected: {tracking_id} - {reject_reason}")

    def log_execution_timeout_event(self, tracking_id: str, **kwargs):
        """
        记录执行超时事件（实盘交易）

        必需字段: tracking_id
        可选字段: symbol, expected_volume, delay_seconds

        Example:
            >>> GLOG.log_execution_timeout_event(
            ...     tracking_id="track-123",
            ...     symbol="000001.SZ",
            ...     delay_seconds=30
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="EXECUTIONTIMEOUT",
            tracking_id=tracking_id,
            **kwargs
        )
        self.ERROR(f"Execution timeout: {tracking_id}")

    def log_execution_confirm_event(
        self,
        tracking_id: str,
        expected_price: Number,
        actual_price: Number,
        expected_volume: int,
        actual_volume: int,
        **kwargs
    ):
        """
        记录执行确认事件（实盘交易）

        必需字段: tracking_id, expected_price, actual_price, expected_volume, actual_volume
        可选字段: symbol, direction, slippage, delay_seconds, commission, price_deviation, volume_deviation

        Example:
            >>> GLOG.log_execution_confirm_event(
            ...     tracking_id="track-123",
            ...     expected_price=10.50,
            ...     actual_price=10.52,
            ...     expected_volume=1000,
            ...     actual_volume=1000,
            ...     symbol="000001.SZ",
            ...     slippage=0.02
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="EXECUTIONCONFIRMATION",
            tracking_id=tracking_id,
            expected_price=expected_price,
            actual_price=actual_price,
            expected_volume=expected_volume,
            actual_volume=actual_volume,
            **kwargs
        )
        self.INFO(f"Execution confirmed: {tracking_id}")

    def log_execution_cancel_event(self, tracking_id: str, cancel_reason: str, **kwargs):
        """
        记录执行取消事件（实盘交易）

        必需字段: tracking_id, cancel_reason
        可选字段: symbol, direction, cancel_time

        Example:
            >>> GLOG.log_execution_cancel_event(
            ...     tracking_id="track-123",
            ...     cancel_reason="策略停止",
            ...     symbol="000001.SZ"
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="EXECUTIONCANCELLATION",
            tracking_id=tracking_id,
            cancel_reason=cancel_reason,
            **kwargs
        )
        self.WARN(f"Execution cancelled: {tracking_id} - {cancel_reason}")

    def log_engine_error_event(self, error_code: str, error_message: str, **kwargs):
        """
        记录引擎错误事件

        必需字段: error_code, error_message
        可选字段: engine_id, task_id, progress

        Example:
            >>> GLOG.log_engine_error_event(
            ...     error_code="DATA_LOAD_FAILED",
            ...     error_message="无法加载数据: 000001.SZ",
            ...     engine_id=engine.uuid
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="ENGINEERROR",
            error_code=error_code,
            error_message=error_message,
            **kwargs
        )
        self.ERROR(f"Engine error: [{error_code}] {error_message}")

    def log_engine_start_event(self, **kwargs):
        """
        记录引擎启动事件

        可选字段: engine_id, task_id, portfolio_id, start_time, config

        Example:
            >>> GLOG.log_engine_start_event(
            ...     engine_id=engine.uuid,
            ...     task_id=run.uuid,
            ...     portfolio_id=portfolio.uuid,
            ...     start_time=datetime.now()
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="ENGINESTART",
            **kwargs
        )
        self.INFO("Engine started")

    def log_engine_pause_event(self, reason: str = "", **kwargs):
        """
        记录引擎暂停事件

        必需字段: reason (可选，为空表示正常暂停)
        可选字段: engine_id, task_id, progress, pause_time

        Example:
            >>> GLOG.log_engine_pause_event(
            ...     reason="用户暂停",
            ...     engine_id=engine.uuid,
            ...     progress=0.5
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="ENGINEPAUSE",
            pause_reason=reason,
            **kwargs
        )
        self.WARN(f"Engine paused: {reason if reason else 'No reason'}")

    def log_engine_resume_event(self, **kwargs):
        """
        记录引擎恢复事件

        可选字段: engine_id, task_id, resume_time, paused_duration

        Example:
            >>> GLOG.log_engine_resume_event(
            ...     engine_id=engine.uuid,
            ...     task_id=run.uuid,
            ...     resume_time=datetime.now()
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="ENGINERESUME",
            **kwargs
        )
        self.INFO("Engine resumed")

    def log_engine_complete_event(self, **kwargs):
        """
        记录引擎完成事件

        可选字段: engine_id, task_id, portfolio_id, end_time, duration_seconds,
                  total_bars, total_orders, final_capital, total_return

        Example:
            >>> GLOG.log_engine_complete_event(
            ...     engine_id=engine.uuid,
            ...     task_id=run.uuid,
            ...     duration_seconds=3600,
            ...     total_bars=1000,
            ...     final_capital=110000.0,
            ...     total_return=0.1
            ... )
        """
        self.set_log_category("backtest")
        self.bind_context(
            event_type="ENGINECOMPLETE",
            **kwargs
        )
        self.INFO("Engine completed")


# ==================== 简洁分组 API ====================
# API分层设计：
# 1. GLOG.backtest.*      - 回测业务日志（按事件性质分组）
# 2. GLOG.execution.*     - 实盘执行日志（独立命名空间）
# 3. GLOG.component.*     - 组件日志
# 4. GLOG.performance.*   - 性能日志
#
# 使用示例:
#   GLOG.backtest.trade.signal(symbol, direction)
#   GLOG.backtest.order.reject(order_id, code, reason)
#   GLOG.execution.confirm(tracking_id, expected_price, actual_price, ...)


class _BacktestTradeNamespace:
    """回测交易流程命名空间 - 正常交易流程事件"""

    def __init__(self, logger: GinkgoLogger):
        self._logger = logger

    def signal(self, symbol: str, direction: str, **kwargs):
        """记录信号事件"""
        self._logger.log_signal_event(symbol, direction, **kwargs)

    def order(self, order_id: str, **kwargs):
        """记录订单提交事件"""
        self._logger.log_order_event(order_id, **kwargs)

    def fill(self, order_id: str, price: Number, volume: int, **kwargs):
        """记录订单成交事件"""
        self._logger.log_order_fill_event(order_id, price, volume, **kwargs)

    def position(self, symbol: str, volume: int, **kwargs):
        """记录持仓事件"""
        self._logger.log_position_event(symbol, volume, **kwargs)

    def capital(self, total: Number, cash: Number, **kwargs):
        """记录资金事件"""
        self._logger.log_capital_event(total, cash, **kwargs)


class _BacktestOrderNamespace:
    """回测订单异常命名空间 - 订单异常处理事件"""

    def __init__(self, logger: GinkgoLogger):
        self._logger = logger

    def reject(self, order_id: str, code: str, reason: str, **kwargs):
        """记录订单拒绝事件"""
        self._logger.log_order_rejected_event(order_id, code, reason, **kwargs)

    def cancel(self, order_id: str, reason: str, **kwargs):
        """记录订单取消事件"""
        self._logger.log_order_cancelled_event(order_id, reason, **kwargs)

    def expire(self, order_id: str, reason: str, **kwargs):
        """记录订单过期事件"""
        self._logger.log_order_expired_event(order_id, reason, **kwargs)

    def ack(self, order_id: str, broker_order_id: str, **kwargs):
        """记录订单确认事件（实盘交易）"""
        self._logger.log_order_ack_event(order_id, broker_order_id, **kwargs)


class _BacktestSystemNamespace:
    """回测系统事件命名空间 - 系统级事件"""

    def __init__(self, logger: GinkgoLogger):
        self._logger = logger

    # ========== 引擎状态事件 ==========
    def start(self, **kwargs):
        """记录引擎启动事件"""
        self._logger.log_engine_start_event(**kwargs)

    def pause(self, reason: str = "", **kwargs):
        """记录引擎暂停事件"""
        self._logger.log_engine_pause_event(reason, **kwargs)

    def resume(self, **kwargs):
        """记录引擎恢复事件"""
        self._logger.log_engine_resume_event(**kwargs)

    def complete(self, **kwargs):
        """记录引擎完成事件"""
        self._logger.log_engine_complete_event(**kwargs)

    # ========== 错误和风控事件 ==========
    def error(self, code: str, message: str, **kwargs):
        """记录引擎错误事件"""
        self._logger.log_engine_error_event(code, message, **kwargs)

    def risk(self, risk_type: str, reason: str, **kwargs):
        """记录风控事件"""
        self._logger.log_risk_event(risk_type, reason, **kwargs)


class _BacktestLogNamespace:
    """回测日志主命名空间 - 按事件性质分组访问"""

    def __init__(self, logger: GinkgoLogger):
        self._logger = logger
        # 交易流程事件
        self.trade = _BacktestTradeNamespace(logger)
        # 订单异常事件
        self.order = _BacktestOrderNamespace(logger)
        # 系统事件
        self.system = _BacktestSystemNamespace(logger)

    # ========== 快捷访问（最常用的方法直接暴露） ==========
    def signal(self, symbol: str, direction: str, **kwargs):
        """快捷访问：记录信号事件"""
        self.trade.signal(symbol, direction, **kwargs)

    def fill(self, order_id: str, price: Number, volume: int, **kwargs):
        """快捷访问：记录订单成交事件"""
        self.trade.fill(order_id, price, volume, **kwargs)

    def risk(self, risk_type: str, reason: str, **kwargs):
        """快捷访问：记录风控事件"""
        self.system.risk(risk_type, reason, **kwargs)


class _ExecutionLogNamespace:
    """实盘执行日志命名空间 - 实盘交易执行事件"""

    def __init__(self, logger: GinkgoLogger):
        self._logger = logger

    def confirm(self, tracking_id: str, expected_price: Number, actual_price: Number,
                expected_volume: int, actual_volume: int, **kwargs):
        """记录执行确认事件"""
        self._logger.log_execution_confirm_event(
            tracking_id, expected_price, actual_price, expected_volume, actual_volume, **kwargs
        )

    def reject(self, tracking_id: str, reason: str, **kwargs):
        """记录执行拒绝事件"""
        self._logger.log_execution_rejected_event(tracking_id, reason, **kwargs)

    def timeout(self, tracking_id: str, **kwargs):
        """记录执行超时事件"""
        self._logger.log_execution_timeout_event(tracking_id, **kwargs)

    def cancel(self, tracking_id: str, reason: str, **kwargs):
        """记录执行取消事件"""
        self._logger.log_execution_cancel_event(tracking_id, reason, **kwargs)


class _ComponentLogNamespace:
    """组件日志命名空间"""

    def __init__(self, logger: GinkgoLogger):
        self._logger = logger

    def info(self, name: str, message: str, **kwargs):
        """记录组件日志"""
        self._logger.log_component_event(name, message, **kwargs)


class _PerformanceLogNamespace:
    """性能日志命名空间"""

    def __init__(self, logger: GinkgoLogger):
        self._logger = logger

    def metric(self, func: str, duration_ms: Number, **kwargs):
        """记录性能指标"""
        self._logger.log_performance_event(func, duration_ms, **kwargs)
