import os
import logging
import colorlog
import threading
from ginkgo.libs.ginkgo_conf import GINKGOCONF as g_conf

# Read Configure
LOGGING_LEVEL_CONSOLE = g_conf.LOGGING_LEVEL_CONSOLE
LOGGING_LEVEL_FILE = g_conf.LOGGING_LEVEL_FILE
LOGGING_COLOR = g_conf.LOGGING_COLOR
LOGGING_PATH = g_conf.LOGGING_PATH
LOGGIN_DEFAULT_FILE = g_conf.LOGGING_DEFAULT_FILE
LOGGING_FILE_ON = g_conf.LOGGING_FILE_ON


class GinkgoLogger(object):
    # singleton
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(GinkgoLogger, "_instance"):
            with GinkgoLogger._instance_lock:
                if not hasattr(GinkgoLogger, "_instance"):
                    GinkgoLogger._instance = object.__new__(cls)
        return GinkgoLogger._instance

    def __init__(self, logger_name, file_name=None) -> None:
        super().__init__()

        os.system(f"mkdir {LOGGING_PATH}")

        if file_name:
            self.file_name = file_name
        else:
            self.file_name = LOGGIN_DEFAULT_FILE

        self.logger = logging.getLogger(logger_name)
        console_handler = logging.StreamHandler()
        self.file_handler = logging.FileHandler(
            filename=LOGGING_PATH + self.file_name, encoding="utf-8", mode="a"
        )

        # 设置日志级别，会以最高级别为准
        self.logger.setLevel(logging.DEBUG)
        console_handler.setLevel(self.get_log_level(LOGGING_LEVEL_CONSOLE))
        self.file_handler.setLevel(self.get_log_level(LOGGING_LEVEL_FILE))

        # 日志输出格式
        file_formatter = logging.Formatter(
            fmt="[%(asctime)s.%(msecs)03d][%(levelname)s]:%(message)s  %(filename)s -> %(funcName)s line:%(lineno)d ",
            datefmt="%Y-%m-%d  %H:%M:%S",
        )
        console_formatter = colorlog.ColoredFormatter(
            # fmt="%(log_color)s%(asctime) s[%(levelname)s] %(message)s [%(filename)s->%(funcName)s L:%(lineno)d]",
            fmt="%(log_color)s%(asctime) s %(message)s [%(filename)s->%(funcName)s L:%(lineno)d]",
            # datefmt="%Y-%m-%d %H:%M:%S",
            datefmt="%H:%M:%S",
            log_colors=LOGGING_COLOR,
        )
        console_handler.setFormatter(console_formatter)
        self.file_handler.setFormatter(file_formatter)

        # 添加日志处理
        self.logger.addHandler(console_handler)
        if LOGGING_FILE_ON:
            self.logger.addHandler(self.file_handler)

    def reset_logfile(self, file_name: str):
        if not LOGGING_FILE_ON:
            return
        self.logger.removeHandler(self.file_handler)
        self.file_handler = logging.FileHandler(
            filename=LOGGING_PATH + file_name, encoding="utf-8", mode="a"
        )
        file_formatter = logging.Formatter(
            fmt="[%(asctime)s.%(msecs)03d][%(levelname)s]:%(message)s  %(filename)s -> %(funcName)s line:%(lineno)d ",
            datefmt="%Y-%m-%d  %H:%M:%S",
        )
        self.file_handler.setFormatter(file_formatter)
        self.logger.addHandler(self.file_handler)

    def get_log_level(self, level):
        r = 10
        if level == "DEBUG":
            r = 10
        elif level == "INFO":
            r = 20
        elif level == "WARNING":
            r = 30
        elif level == "ERROR":
            r = 40
        elif level == "CRITICAL":
            r = 50
        return r


GINKGOLOGGER = GinkgoLogger("ginkgo_log")
