# Upstream: 全局所有模块 (通过GLOG单例记录日志)
# Downstream: structlog, contextvars(分布式追踪trace_id/span_id), Number/to_decimal(类型支持), datetime
# Role: GinkgoLogger结构化日志核心，基于structlog实现JSON/Rich双输出，支持trace_id/span_id分布式追踪和业务上下文绑定


# Imports for structlog and distributed logging
import contextvars
import contextlib
import platform
import structlog
from datetime import datetime, date
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
_business_context_ctx: contextvars.ContextVar[Optional[Any]] = contextvars.ContextVar(
    "business_context", default=None
)






from typing import List
import sys
import os
import inspect
import logging
import threading
import hashlib
import time
import re

# #3900: 线程本地存储，用于 Filter 在 emit 前修补 LogRecord 的调用方
_caller_local = threading.local()
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from rich.console import Console
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

    从 EngineContext/PortfolioContext 引用读取 task-level 字段，
    从 _ginkgo event_dict key 读取 event-level 字段。

    Args:
        logger: structlog logger对象
        log_method: 日志方法
        event_dict: 日志事件字典

    Returns:
        Dict: 更新后的日志事件字典
    """
    if "ginkgo" not in event_dict:
        event_dict["ginkgo"] = {}

    # 1. Task-level fields from EngineContext reference
    engine_ctx = _business_context_ctx.get()
    if engine_ctx is not None:
        if hasattr(engine_ctx, 'task_id') and engine_ctx.task_id:
            event_dict["ginkgo"]["task_id"] = engine_ctx.task_id
        if hasattr(engine_ctx, 'engine_id') and engine_ctx.engine_id:
            event_dict["ginkgo"]["engine_id"] = engine_ctx.engine_id
        if hasattr(engine_ctx, 'source_type') and engine_ctx.source_type is not None:
            event_dict["ginkgo"]["source_type"] = engine_ctx.source_type.value if hasattr(engine_ctx.source_type, 'value') else engine_ctx.source_type
        if hasattr(engine_ctx, 'business_timestamp') and engine_ctx.business_timestamp:
            event_dict["ginkgo"]["business_timestamp"] = engine_ctx.business_timestamp
        if hasattr(engine_ctx, 'portfolio_id') and engine_ctx.portfolio_id:
            event_dict["ginkgo"]["portfolio_id"] = engine_ctx.portfolio_id

    # 2. Event-level fields from _ginkgo kwargs
    event_fields = event_dict.pop("_ginkgo", {})
    event_dict["ginkgo"].update(event_fields)

    # 3. log_category
    log_category = _log_category_ctx.get()
    if log_category:
        event_dict["ginkgo"]["log_category"] = log_category

    # 4. trace_id / span_id
    trace_id = _trace_id_ctx.get()
    span_id = _span_id_ctx.get()
    if trace_id or span_id:
        event_dict["trace"] = {}
        if trace_id:
            event_dict["trace"]["id"] = trace_id
        if span_id:
            event_dict["trace"]["span_id"] = span_id

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
        import logging; logging.getLogger(__name__).debug("optional import unavailable")
        pass

    return event_dict


def _datetime_decimal_serializer(logger, method_name, event_dict):
    """将 datetime/Decimal 转为 JSON 兼容类型"""
    for key, value in list(event_dict.items()):
        if isinstance(value, Decimal):
            event_dict[key] = float(value)
        elif isinstance(value, datetime):
            event_dict[key] = value.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(value, date):
            event_dict[key] = value.strftime('%Y-%m-%d')
        elif isinstance(value, dict):
            for k2, v2 in list(value.items()):
                if isinstance(v2, Decimal):
                    value[k2] = float(v2)
                elif isinstance(v2, datetime):
                    value[k2] = v2.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
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


# ==================== #3900: 调用方来源处理器 ====================


def caller_processor(logger, log_method, event_dict):
    """
    调用方来源处理器 (相关issue: #3900)

    从 _caller_local（线程本地）读取调用方信息，映射为 ECS 标准的
    log.origin 字段。单一数据源：_caller_local 由 _emit() 设置，
    同时被本处理器（JSON 输出）和 _CallerPatchFilter（控制台输出）消费。
    """
    caller = getattr(_caller_local, 'caller', None)
    if caller:
        if "log" in event_dict:
            event_dict["log"]["origin"] = caller
        else:
            event_dict["log"] = {"origin": caller}
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
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.UnicodeDecoder(),
                # === 快速处理器（简单逻辑）===
                ginkgo_processor,
                masking_processor,
                # === 中等处理器（格式化）===
                structlog.processors.TimeStamper(fmt="iso"),
                ecs_processor,
                caller_processor,  # #3900: 调用方来源信息（必须在 ecs_processor 之后，因为 ecs 会覆盖 log 字段）
                # === 慢速处理器（可选）===
                container_metadata_processor,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                # === 最后：交给 stdlib Handler 的 ProcessorFormatter 做最终渲染 ===
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
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

        if not os.path.exists(LOGGING_PATH):
            Path(LOGGING_PATH).mkdir(parents=True, exist_ok=True)
            print(f"Create folder {LOGGING_PATH}")

        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        # 错误追踪相关的实例变量
        self._error_patterns = {}  # 错误模式计数 {pattern_hash: count}
        self._error_timestamps = {}  # 错误时间戳 {pattern_hash: last_log_time}
        self._error_lock = threading.RLock()  # 线程安全锁
        self._max_error_history = 1000  # 最大错误历史记录数

        # 配置 structlog 和 handlers
        configure_structlog()

        self._setup_handlers(console_log)

        # 初始化分组命名空间（简洁API）
        self.backtest = _BacktestLogNamespace(self)
        self.component = _ComponentLogNamespace(self)
        self.performance = _PerformanceLogNamespace(self)

    def _setup_handlers(self, console_log):
        # 防止重复初始化（ginkgo.libs vs src.ginkgo.libs 可能触发两次 __init__）
        existing_names = {getattr(h, '_name', None) for h in self.logger.handlers}

        if LOGGING_FILE_ON:
            file_handler_name = f"json_file_handler_{self.logger_name}.log"
            if file_handler_name not in existing_names:
                self._setup_json_file_handler()

        console_name = getattr(self, '_console_handler_name', None)
        if console_name and console_name not in existing_names:
            self._setup_console_handler(console_log)

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
        JSON 格式文件日志处理器

        使用 structlog ProcessorFormatter 输出 JSON，供 Vector 采集。
        """
        if not self._file_names:
            self._file_names = [LOGGING_DEFAULT_FILE]

        for file_name in self._file_names:
            if not file_name.endswith(".log"):
                file_name += ".log"

            file_path = os.path.join(LOGGING_PATH, file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            file_handler = RotatingFileHandler(
                filename=file_path,
                encoding="utf-8",
                mode="a",
                maxBytes=self.max_file_bytes,
                backupCount=self.backup_count,
            )
            file_handler.set_name(f"json_{self.gen_file_handler_name(file_name)}")
            file_handler.setLevel(self.get_log_level(LOGGING_LEVEL_FILE))
            file_handler.setFormatter(self._make_json_formatter())
            self.file_handlers.append(file_handler)
            self.logger.addHandler(file_handler)

    @staticmethod
    def _make_json_formatter():
        """创建 structlog ProcessorFormatter（JSON 输出）"""
        import structlog
        return structlog.stdlib.ProcessorFormatter(
            processors=[
                lambda logger, name, ed: (ed.pop("_record", None), ed.pop("_from_structlog", None), ed)[2],
                _datetime_decimal_serializer,
                structlog.processors.JSONRenderer(),
            ]
        )

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
        file_handler.setFormatter(self._make_json_formatter())
        self.file_handlers.append(file_handler)
        self.logger.addHandler(file_handler)
        return file_handler

    def _setup_console_handler(self, console_log):
        self.console_handler = RichHandler(
            show_time=True,
            omit_repeated_times=False,
            rich_tracebacks=True,
            log_time_format="[%X]",
            # #6465: 诊断日志走 stderr，保留 stdout 给 CLI 业务输出（如 -r 纯 JSON）。
            # 本 rich 版本裸 RichHandler 默认写 stdout，会污染机器可读输出。
            console=Console(stderr=True),
        )
        self.console_handler.set_name(self._console_handler_name)
        self.console_handler.setLevel(self.get_log_level(LOGGING_LEVEL_CONSOLE))
        import structlog

        # #3900: Filter 在 emit() 之前运行，修补 LogRecord 的 pathname/lineno
        # RichHandler.emit() 在调用 format() 之前就读取 record.pathname，
        # 所以不能在 ProcessorFormatter 里修补，必须用 Filter。
        # Filter 从 _caller_local（线程本地）读取调用方信息，
        # 由 INFO/DEBUG/ERROR 等方法在调用 structlog 前写入。
        class _CallerPatchFilter(logging.Filter):
            def filter(self, record):
                caller = getattr(_caller_local, 'caller', None)
                if caller:
                    record.pathname = caller.get('file', record.pathname)
                    record.lineno = caller.get('line', record.lineno)
                    record.funcName = caller.get('func', record.funcName)
                    _caller_local.caller = None
                return True

        self.console_handler.addFilter(_CallerPatchFilter())

        self.console_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processors=[
                    lambda logger, name, ed: ed.get("event", "") or ed.get("message", ""),
                ]
            )
        )

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
        error_handler.setFormatter(self._make_json_formatter())
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
        # 通过 _emit 统一发射，caller 信息自动注入
        level_map = {
            "DEBUG": "debug", "INFO": "info", "WARNING": "warning",
            "WARN": "warning", "ERROR": "error", "CRITICAL": "critical",
        }
        structlog_level = level_map.get(level.upper(), level.lower())
        self._emit(structlog_level, msg)

    def DEBUG(self, msg: str) -> None:
        """记录 DEBUG 级别日志"""
        if not self.logger.isEnabledFor(logging.DEBUG):
            return

        # T116: 生产环境 DEBUG 日志采样（减少日志量）
        sampling_rate = getattr(GCONF, 'LOGGING_SAMPLING_RATE', 0.1)
        if sampling_rate < 1.0:
            import random
            if random.random() > sampling_rate:
                return

        # #3900: 调用方来源通过 _emit 统一注入
        self._emit("debug", msg)

    def INFO(self, msg: str) -> None:
        """记录 INFO 级别日志"""
        if not self.logger.isEnabledFor(logging.INFO):
            return

        self._emit("info", msg)

    def WARN(self, msg: str) -> None:
        """记录 WARNING 级别日志"""
        if not self.logger.isEnabledFor(logging.WARNING):
            return

        self._emit("warning", msg)

    def WARNING(self, msg: str) -> None:
        """记录 WARNING 级别日志（WARN 方法的别名）"""
        if not self.logger.isEnabledFor(logging.WARNING):
            return

        self._emit("warning", msg)

    def ERROR(self, msg: str) -> None:
        """记录 ERROR 级别日志（含智能流量控制）"""
        if not self.logger.isEnabledFor(logging.ERROR):
            return

        should_log, processed_msg = self._should_log_error(msg)
        if should_log:
            self._emit("error", processed_msg)

    def CRITICAL(self, msg: str) -> None:
        """记录 CRITICAL 级别日志"""
        if not self.logger.isEnabledFor(logging.CRITICAL):
            return

        self._emit("critical", msg)

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

    def bind_context(self, engine_context=None) -> None:
        """
        Bind engine context reference.

        Args:
            engine_context: EngineContext or PortfolioContext instance reference
        """
        if engine_context is not None:
            from ginkgo.trading.context.engine_context import EngineContext
            from ginkgo.trading.context.portfolio_context import PortfolioContext
            if not isinstance(engine_context, (EngineContext, PortfolioContext)):
                raise TypeError(
                    f"bind_context only accepts EngineContext/PortfolioContext, got {type(engine_context).__name__}"
                )
            _business_context_ctx.set(engine_context)

    def clear_context(self) -> None:
        """Clear context reference and log category"""
        _business_context_ctx.set(None)
        _log_category_ctx.set(None)

    # ==================== 内部辅助方法 ====================

    def _emit(self, level: str, msg: str, **kwargs) -> None:
        """
        统一日志发射入口 (#3900)

        封装调用方来源注入 + structlog 调用 + thread-local 清理。
        所有公开日志方法（DEBUG/INFO/WARN/ERROR/CRITICAL 及 log_*_event）
        都应通过此方法发射，确保调用方信息一致。

        Args:
            level: structlog 方法名 ("debug"/"info"/"warning"/"error"/"critical")
            msg: 日志消息
            **kwargs: 传递给 structlog 的额外字段（如 _ginkgo）
        """
        frame = sys._getframe(2)
        _caller = {"file": frame.f_code.co_filename, "line": frame.f_lineno, "func": frame.f_code.co_name}
        _caller_local.caller = _caller
        try:
            getattr(structlog.get_logger(self.logger_name), level)(msg, **kwargs)
        finally:
            _caller_local.caller = None

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

    def log_signal_event(self, symbol: str, direction: str, msg: str = None, **kwargs):
        """
        记录信号事件

        必需字段: symbol, direction
        可选字段: signal_volume, signal_reason, signal_weight, signal_confidence, strategy_id, msg

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
        self._emit("info", 
            msg or f"Signal generated: {direction} {symbol}",
            _ginkgo={
                "event_type": "SIGNALGENERATION",
                "symbol": symbol,
                "direction": direction,
                **kwargs
            }
        )

    def log_order_event(self, order_id: str, msg: str = None, **kwargs):
        """
        记录订单事件

        必需字段: order_id
        可选字段: order_type, limit_price, frozen_money, symbol, direction, msg

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
        self._emit("info", 
            msg or f"Order submitted: {order_id}",
            _ginkgo={
                "event_type": "ORDERSUBMITTED",
                "order_id": order_id,
                **kwargs
            }
        )

    def log_order_fill_event(self, order_id: str, price: Number, volume: int, msg: str = None, **kwargs):
        """
        记录成交事件

        必需字段: order_id, transaction_price, transaction_volume
        可选字段: trade_id, commission, slippage, msg

        Args:
            order_id: 订单ID
            price: 成交价格 (支持 float/int/Decimal)
            volume: 成交数量
            msg: 自定义消息（可选，默认自动生成）
            **kwargs: 其他字段，如 commission (支持 float/int/Decimal), slippage

        Example:
            >>> GLOG.log_order_fill_event(
            ...     order_id=order.uuid,
            ...     price=10.52,
            ...     volume=1000,
            ...     commission=5.26
            ... )
        """
        self.set_log_category("backtest")
        self._emit("info", 
            msg or f"Order filled: {order_id} @ {price} x{volume}",
            _ginkgo={
                "event_type": "ORDERFILLED",
                "order_id": order_id,
                "transaction_price": price,
                "transaction_volume": volume,
                **kwargs
            }
        )

    def log_position_event(self, symbol: str, volume: int, msg: str = None, **kwargs):
        """
        记录持仓事件

        必需字段: position_code, position_volume
        可选字段: position_cost, position_price, msg

        Example:
            >>> GLOG.log_position_event(
            ...     symbol="000001.SZ",
            ...     volume=1000,
            ...     position_cost=10520.00
            ... )
        """
        self.set_log_category("backtest")
        self._emit("info", 
            msg or f"Position updated: {symbol} {volume} shares",
            _ginkgo={
                "event_type": "POSITIONUPDATE",
                "position_code": symbol,
                "position_volume": volume,
                **kwargs
            }
        )

    def log_capital_event(self, total_value: Number, available_cash: Number, msg: str = None, **kwargs):
        """
        记录资金事件

        必需字段: total_value, available_cash (支持 float/int/Decimal)
        可选字段: net_value, drawdown, pnl, msg

        Example:
            >>> GLOG.log_capital_event(
            ...     total_value=100000.00,
            ...     available_cash=50000.00,
            ...     pnl=5000.00
            ... )
        """
        self.set_log_category("backtest")
        self._emit("info", 
            msg or f"Capital updated: total={total_value}, cash={available_cash}",
            _ginkgo={
                "event_type": "CAPITALUPDATE",
                "total_value": total_value,
                "available_cash": available_cash,
                **kwargs
            }
        )

    def log_risk_event(self, risk_type: str, risk_reason: str, msg: str = None, **kwargs):
        """
        记录风控事件

        必需字段: risk_type, risk_reason
        可选字段: risk_limit_value, risk_actual_value, msg

        Example:
            >>> GLOG.log_risk_event(
            ...     risk_type="POSITION_LIMIT",
            ...     risk_reason="单股持仓超限",
            ...     risk_limit_value=0.2,
            ...     risk_actual_value=0.25
            ... )
        """
        self.set_log_category("backtest")
        self._emit("warning", 
            msg or f"Risk event: {risk_type} - {risk_reason}",
            _ginkgo={
                "event_type": "RISKBREACH",
                "risk_type": risk_type,
                "risk_reason": risk_reason,
                **kwargs
            }
        )

    def log_component_event(self, component_name: str, message: str = None, msg: str = None, **kwargs):
        """
        记录组件日志

        必需字段: component_name
        可选字段: message, component_version, component_instance, module_name

        Example:
            >>> GLOG.log_component_event(
            ...     component_name="Strategy",
            ...     component_version="1.0.0",
            ...     message="策略初始化完成"
            ... )
        """
        self.set_log_category("component")
        actual_msg = msg or message or f"Component event: {component_name}"
        self._emit("info", 
            actual_msg,
            _ginkgo={
                "component_name": component_name,
                **kwargs
            }
        )

    def log_performance_event(self, function_name: str, duration_ms: float, msg: str = None, **kwargs):
        """
        记录性能日志

        必需字段: function_name, duration_ms
        可选字段: memory_mb, cpu_percent, throughput, module_name, call_site, msg

        Example:
            >>> GLOG.log_performance_event(
            ...     function_name="calculate_signals",
            ...     duration_ms=125.5,
            ...     memory_mb=256.8,
            ...     module_name="ginkgo.trading.strategies"
            ... )
        """
        self.set_log_category("performance")
        self._emit("info", 
            msg or f"Performance: {function_name} took {duration_ms}ms",
            _ginkgo={
                "function_name": function_name,
                "duration_ms": duration_ms,
                **kwargs
            }
        )

    # ==================== 错误事件便捷方法 ====================

    def log_order_rejected_event(self, order_id: str, reject_code: str, reject_reason: str, msg: str = None, **kwargs):
        """
        记录订单拒绝事件

        必需字段: order_id, reject_code, reject_reason
        可选字段: symbol, direction, limit_price, msg

        Example:
            >>> GLOG.log_order_rejected_event(
            ...     order_id=order.uuid,
            ...     reject_code="INSUFFICIENT_FUNDS",
            ...     reject_reason="可用资金不足",
            ...     symbol="000001.SZ"
            ... )
        """
        self.set_log_category("backtest")
        self._emit("error", 
            msg or f"Order rejected: {order_id} - {reject_code}: {reject_reason}",
            _ginkgo={
                "event_type": "ORDERREJECTED",
                "order_id": order_id,
                "reject_code": reject_code,
                "reject_reason": reject_reason,
                **kwargs
            }
        )

    def log_order_cancelled_event(self, order_id: str, cancel_reason: str, msg: str = None, **kwargs):
        """
        记录订单取消事件

        必需字段: order_id, cancel_reason
        可选字段: cancelled_quantity, msg

        Example:
            >>> GLOG.log_order_cancelled_event(
            ...     order_id=order.uuid,
            ...     cancel_reason="用户取消",
            ...     cancelled_quantity=500
            ... )
        """
        self.set_log_category("backtest")
        self._emit("warning", 
            msg or f"Order cancelled: {order_id} - {cancel_reason}",
            _ginkgo={
                "event_type": "ORDERCANCELACK",
                "order_id": order_id,
                "cancel_reason": cancel_reason,
                **kwargs
            }
        )

    def log_order_ack_event(self, order_id: str, broker_order_id: str, msg: str = None, **kwargs):
        """
        记录订单确认事件（实盘交易）

        必需字段: order_id, broker_order_id
        可选字段: symbol, direction, limit_price, ack_message, order_status, msg

        Example:
            >>> GLOG.log_order_ack_event(
            ...     order_id=order.uuid,
            ...     broker_order_id="broker-12345",
            ...     symbol="000001.SZ",
            ...     order_status="ACCEPTED"
            ... )
        """
        self.set_log_category("backtest")
        self._emit("info", 
            msg or f"Order acknowledged: {order_id} -> {broker_order_id}",
            _ginkgo={
                "event_type": "ORDERACK",
                "order_id": order_id,
                "broker_order_id": broker_order_id,
                **kwargs
            }
        )

    def log_order_expired_event(self, order_id: str, expire_reason: str, msg: str = None, **kwargs):
        """
        记录订单过期事件

        必需字段: order_id, expire_reason
        可选字段: expired_quantity, msg

        Example:
            >>> GLOG.log_order_expired_event(
            ...     order_id=order.uuid,
            ...     expire_reason="订单有效期已过",
            ...     expired_quantity=1000
            ... )
        """
        self.set_log_category("backtest")
        self._emit("warning", 
            msg or f"Order expired: {order_id} - {expire_reason}",
            _ginkgo={
                "event_type": "ORDEREXPIRED",
                "order_id": order_id,
                "expire_reason": expire_reason,
                **kwargs
            }
        )

    def log_engine_error_event(self, error_code: str, error_message: str, msg: str = None, **kwargs):
        """
        记录引擎错误事件

        必需字段: error_code, error_message
        可选字段: engine_id, task_id, progress, msg

        Example:
            >>> GLOG.log_engine_error_event(
            ...     error_code="DATA_LOAD_FAILED",
            ...     error_message="无法加载数据: 000001.SZ",
            ...     engine_id=engine.uuid
            ... )
        """
        self.set_log_category("backtest")
        self._emit("error", 
            msg or f"Engine error: [{error_code}] {error_message}",
            _ginkgo={
                "event_type": "ENGINEERROR",
                "error_code": error_code,
                "error_message": error_message,
                **kwargs
            }
        )

    def log_t1_settlement_event(self, settled_count: int, msg: str = None, **kwargs):
        self.set_log_category("backtest")
        self._emit("info", 
            msg or f"T+1 settlement: {settled_count} positions unfrozen",
            _ginkgo={"event_type": "T1SETTLEMENT", "settled_count": settled_count, **kwargs}
        )

    def log_t1_delay_event(self, code: str, reason: str, msg: str = None, **kwargs):
        self.set_log_category("backtest")
        self._emit("warning", 
            msg or f"T+1 delay: {code} - {reason}",
            _ginkgo={"event_type": "T1DELAYDECISION", "symbol": code, "reason": reason, **kwargs}
        )

    def log_time_advance_event(self, time, position_count: int, delayed_count: int, cash: float, msg: str = None, **kwargs):
        self.set_log_category("backtest")
        self._emit("info", 
            msg or f"Time advance: {time}, {position_count} positions, {delayed_count} delayed",
            _ginkgo={"event_type": "TIMEADVANCE", "position_count": position_count, "delayed_count": delayed_count, "cash": cash, **kwargs}
        )

    def log_price_received_event(self, code: str, price: float, msg: str = None, **kwargs):
        self.set_log_category("backtest")
        self._emit("info", 
            msg or f"Price received: {code} close={price}",
            _ginkgo={"event_type": "PRICERECEIVED", "symbol": code, "price": price, **kwargs}
        )

    def log_strategy_signal_event(self, strategy_name: str, signal_count: int, signals_desc: str = "", msg: str = None, **kwargs):
        self.set_log_category("backtest")
        self._emit("info", 
            msg or f"Strategy {strategy_name}: {signal_count} signals",
            _ginkgo={"event_type": "STRATEGYSIGNAL", "strategy_name": strategy_name, "signal_count": signal_count, **kwargs}
        )

    def log_engine_start_event(self, msg: str = None, **kwargs):
        """
        记录引擎启动事件

        可选字段: engine_id, task_id, portfolio_id, start_time, config, msg

        Example:
            >>> GLOG.log_engine_start_event(
            ...     engine_id=engine.uuid,
            ...     task_id=run.uuid,
            ...     portfolio_id=portfolio.uuid,
            ...     start_time=datetime.now()
            ... )
        """
        self.set_log_category("backtest")
        self._emit("info", 
            msg or "Engine started",
            _ginkgo={
                "event_type": "ENGINESTART",
                **kwargs
            }
        )

    def log_engine_pause_event(self, reason: str = "", msg: str = None, **kwargs):
        """
        记录引擎暂停事件

        必需字段: reason (可选，为空表示正常暂停)
        可选字段: engine_id, task_id, progress, pause_time, msg

        Example:
            >>> GLOG.log_engine_pause_event(
            ...     reason="用户暂停",
            ...     engine_id=engine.uuid,
            ...     progress=0.5
            ... )
        """
        self.set_log_category("backtest")
        self._emit("warning", 
            msg or f"Engine paused: {reason if reason else 'No reason'}",
            _ginkgo={
                "event_type": "ENGINEPAUSE",
                "pause_reason": reason,
                **kwargs
            }
        )

    def log_engine_resume_event(self, msg: str = None, **kwargs):
        """
        记录引擎恢复事件

        可选字段: engine_id, task_id, resume_time, paused_duration, msg

        Example:
            >>> GLOG.log_engine_resume_event(
            ...     engine_id=engine.uuid,
            ...     task_id=run.uuid,
            ...     resume_time=datetime.now()
            ... )
        """
        self.set_log_category("backtest")
        self._emit("info", 
            msg or "Engine resumed",
            _ginkgo={
                "event_type": "ENGINERESUME",
                **kwargs
            }
        )

    def log_engine_complete_event(self, msg: str = None, **kwargs):
        """
        记录引擎完成事件

        可选字段: engine_id, task_id, portfolio_id, end_time, duration_seconds,
                  total_bars, total_orders, final_capital, total_return, msg

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
        self._emit("info", 
            msg or "Engine completed",
            _ginkgo={
                "event_type": "ENGINECOMPLETE",
                **kwargs
            }
        )


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
