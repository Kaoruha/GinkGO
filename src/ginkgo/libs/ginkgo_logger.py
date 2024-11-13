# import os
# import time
# import inspect
# import logging
# import colorlog
# import threading
# from logging.handlers import RotatingFileHandler
# from rich.logging import RichHandler

# from ginkgo.libs.ginkgo_conf import GCONF

# # Read Configure
# LOGGING_LEVEL_CONSOLE = GCONF.LOGGING_LEVEL_CONSOLE
# LOGGING_LEVEL_FILE = GCONF.LOGGING_LEVEL_FILE
# LOGGING_COLOR = GCONF.LOGGING_COLOR
# LOGGING_PATH = GCONF.LOGGING_PATH
# LOGGIN_DEFAULT_FILE = GCONF.LOGGING_DEFAULT_FILE
# LOGGING_FILE_ON = GCONF.LOGGING_FILE_ON


# class GinkgoLogger(object):
#     def __init__(self, logger_name, file_name=None, enable_console_log=True) -> None:
#         super().__init__()
#         self.backup_count = 3
#         self.max_file_bytes = 2 * 1024 * 1024 * 1024  # 2GB
#         self._file_handler_name = f"{logger_name}_file_logger"
#         self._console_handler_name = "ginkgo_console_logger"
#         self.file_formatter = logging.Formatter(
#             fmt="[%(asctime)s][%(levelname)s]:%(message)s  ",
#             datefmt="%Y-%m-%d %H:%M:%S",
#         )
#         self.console_formatter = logging.Formatter(
#             "P:%(process)d %(message)s",
#             datefmt="%m-%d %H:%M",
#         )

#         if not os.path.exists(LOGGING_PATH):
#             os.mkdir(LOGGING_PATH)
#             print(f"Create folder {LOGGING_PATH}")

#         self.file_name = file_name if file_name else LOGGIN_DEFAULT_FILE
#         self.logger = logging.getLogger(logger_name)
#         file_path = LOGGING_PATH + self.file_name if LOGGING_PATH.endswith("/") else LOGGING_PATH + "/" + self.file_name

#         self.file_handler = RotatingFileHandler(
#             filename=file_path,
#             encoding="utf-8",
#             mode="a",
#             maxBytes=self.max_file_bytes,
#             backupCount=self.backup_count,
#         )
#         self.file_handler.set_name(self._file_handler_name)

#         # self.console_handler = logging.StreamHandler()
#         self.console_handler = RichHandler(
#             show_time=True,
#             omit_repeated_times=False,
#             rich_tracebacks=True,
#             log_time_format="[%X]",
#         )
#         self.console_handler.set_name(self._console_handler_name)

#         # 设置日志级别，会以最高级别为准
#         self.logger.setLevel(logging.INFO)
#         self.console_handler.setLevel(self.get_log_level(LOGGING_LEVEL_CONSOLE))
#         self.file_handler.setLevel(self.get_log_level(LOGGING_LEVEL_FILE))

#         # 日志输出格式
#         # set the file handler formatter, that print the line num and file that call the logger function

#         self.console_handler.setFormatter(self.console_formatter)
#         self.file_handler.setFormatter(self.file_formatter)

#         # Prevent the child logger from propagating its messages to the root logger
#         self.logger.propagate = False

#         if enable_console_log:
#             is_console_handler_registed = False
#             for h in self.logger.handlers:
#                 if h.name == self._console_handler_name:
#                     is_console_handler_registed = True

#             if not is_console_handler_registed:
#                 self.logger.addHandler(self.console_handler)

#         is_file_handler_registed = False
#         for h in self.logger.handlers:
#             if h.name == self._file_handler_name:
#                 is_file_handler_registed = True
#         # 添加日志处理
#         if LOGGING_FILE_ON:
#             if not is_file_handler_registed:
#                 self.logger.addHandler(self.file_handler)

#         # 异常记录
#         error_path = LOGGING_PATH + self.file_name if LOGGING_PATH.endswith("/") else LOGGING_PATH + "/" + "error.log"
#         error_handler = logging.FileHandler(
#             filename=error_path,
#             encoding="utf-8",
#             mode="a",
#         )
#         error_handler.set_name("ginkgo_error")
#         error_handler.setLevel(logging.ERROR)
#         error_handler.setFormatter(self.file_formatter)
#         self.logger.addHandler(error_handler)

#     def reset_logfile(self, file_name: str) -> None:
#         self.logger.removeHandler(self.file_handler)
#         if not LOGGING_FILE_ON:
#             return
#         file_path = LOGGING_PATH + file_name if LOGGING_PATH.endswith("/") else LOGGING_PATH + "/" + file_name
#         self.file_handler = RotatingFileHandler(
#             filename=file_path,
#             encoding="utf-8",
#             mode="a",
#             maxBytes=self.max_file_bytes,
#             backupCount=self.backup_count,
#         )
#         self.file_handler.setFormatter(self.file_formatter)
#         self.logger.addHandler(self.file_handler)

#     def set_level(self, level: str) -> None:
#         level: int = self.get_log_level(level)
#         self.logger.setLevel(level)
#         self.console_handler.setLevel(level)

#     def get_log_level(self, level: str) -> int:
#         r = 10
#         level = level.upper()
#         if level == "DEBUG":
#             r = 10
#         elif level == "INFO":
#             r = 20
#         elif level == "WARNING":
#             r = 30
#         elif level == "ERROR":
#             r = 40
#         elif level == "CRITICAL":
#             r = 50
#         return r

#     def DEBUG(self, msg: str):
#         caller = inspect.stack()[1]
#         function = caller.function
#         filename = caller.filename.split("/")[-1]
#         lineno = caller.lineno
#         self.logger.debug(f"{msg}  [{filename} -> {function}()  L:{lineno}]")

#     def INFO(self, msg: str):
#         caller = inspect.stack()[1]
#         function = caller.function
#         filename = caller.filename.split("/")[-1]
#         lineno = caller.lineno
#         self.logger.info(f"{msg}  [{filename} -> {function}()  L:{lineno}]")

#     def WARN(self, msg: str):
#         caller = inspect.stack()[1]
#         function = caller.function
#         filename = caller.filename.split("/")[-1]
#         lineno = caller.lineno
#         self.logger.warning(f"{msg}  [{filename} -> {function}()  L:{lineno}]")

#     def ERROR(self, msg: str):
#         caller = inspect.stack()[1]
#         function = caller.function
#         filename = caller.filename.split("/")[-1]
#         lineno = caller.lineno
#         self.logger.error(f"{msg}  [{filename} -> {function}()  L:{lineno}]")

#     def CRITICAL(self, msg: str):
#         caller = inspect.stack()[1]
#         function = caller.function
#         filename = caller.filename.split("/")[-1]
#         lineno = caller.lineno
#         self.logger.critical(f"{msg}  [{filename} -> {function}()  L:{lineno}]")


# GLOG = GinkgoLogger("ginkgo", "ginkgo.log", True)


import os
import inspect
import logging
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from ginkgo.libs.ginkgo_conf import GCONF

# Read Configure
LOGGING_LEVEL_CONSOLE = GCONF.LOGGING_LEVEL_CONSOLE
LOGGING_LEVEL_FILE = GCONF.LOGGING_LEVEL_FILE
LOGGING_COLOR = GCONF.LOGGING_COLOR
LOGGING_PATH = GCONF.LOGGING_PATH
LOGGING_DEFAULT_FILE = GCONF.LOGGING_DEFAULT_FILE
LOGGING_FILE_ON = GCONF.LOGGING_FILE_ON


class GinkgoLogger:
    def __init__(self, logger_name: str, file_name: str = None, enable_console_log=True):
        self.backup_count = 3
        self.max_file_bytes = 2 * 1024 * 1024 * 1024
        self._file_handler_name = f"{logger_name}_file_logger"
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
            os.makedirs(LOGGING_PATH, exist_ok=True)
            print(f"Create folder {LOGGING_PATH}")

        self.file_name = file_name or LOGGING_DEFAULT_FILE
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        self._setup_file_handler()
        self._setup_console_handler(enable_console_log)
        self._setup_error_handler()

    def _setup_file_handler(self):
        file_path = os.path.join(LOGGING_PATH, self.file_name)
        self.file_handler = RotatingFileHandler(
            filename=file_path,
            encoding="utf-8",
            mode="a",
            maxBytes=self.max_file_bytes,
            backupCount=self.backup_count,
        )
        self.file_handler.set_name(self._file_handler_name)
        self.file_handler.setLevel(self.get_log_level(LOGGING_LEVEL_FILE))
        self.file_handler.setFormatter(self.file_formatter)
        self.logger.addHandler(self.file_handler)

    def _setup_console_handler(self, enable_console_log):
        self.console_handler = RichHandler(
            show_time=True,
            omit_repeated_times=False,
            rich_tracebacks=True,
            log_time_format="[%X]",
        )
        self.console_handler.set_name(self._console_handler_name)
        self.console_handler.setLevel(self.get_log_level(LOGGING_LEVEL_CONSOLE))
        self.console_handler.setFormatter(self.console_formatter)

        if enable_console_log:
            self.logger.addHandler(self.console_handler)

    def _setup_error_handler(self):
        error_path = os.path.join(LOGGING_PATH, "error.log")
        error_handler = logging.FileHandler(
            filename=error_path,
            encoding="utf-8",
            mode="a",
        )
        error_handler.set_name("ginkgo_error")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.file_formatter)
        self.logger.addHandler(error_handler)

    def reset_logfile(self, file_name: str) -> None:
        self.logger.removeHandler(self.file_handler)
        if not LOGGING_FILE_ON:
            return
        self.file_name = file_name
        self._setup_file_handler()

    def set_level(self, level: str) -> None:
        level = self.get_log_level(level)
        self.logger.setLevel(level)
        self.console_handler.setLevel(level)
        self.file_handler.setLevel(level)

    def get_log_level(self, level: str) -> int:
        return logging.getLevelName(level.upper())

    def log(self, level, msg: str):
        caller = inspect.stack()[1]
        function = caller.function
        filename = caller.filename.split("/")[-1]
        lineno = caller.lineno
        log_method = getattr(self.logger, level.lower())
        log_method(f"{msg}  [{filename} -> {function}()  L:{lineno}]")

    def DEBUG(self, msg: str):
        self.log("DEBUG", msg)

    def INFO(self, msg: str):
        self.log("INFO", msg)

    def WARN(self, msg: str):
        self.log("WARNING", msg)

    def ERROR(self, msg: str):
        self.log("ERROR", msg)

    def CRITICAL(self, msg: str):
        self.log("CRITICAL", msg)


GLOG = GinkgoLogger("ginkgo", "ginkgo.log", True)
