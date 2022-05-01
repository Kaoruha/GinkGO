import logging
import colorlog
import threading
from ginkgo.config.setting import (
    LOGGING_LEVEL_CONSOLE,
    LOGGING_LEVEL_FILE,
    LOGGING_COLOR,
    LOGGING_PATH,
    LOGGIN_DEFAULT_FILE,
    LOGGING_FILE_ON,
)


class GinkgoLogging(object):
    # singleton
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(GinkgoLogging, "_instance"):
            with GinkgoLogging._instance_lock:
                if not hasattr(GinkgoLogging, "_instance"):
                    GinkgoLogging._instance = object.__new__(cls)
        return GinkgoLogging._instance

    def __init__(self, logger_name, file_name=None) -> None:
        super().__init__()
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
        console_handler.setLevel(LOGGING_LEVEL_CONSOLE)
        self.file_handler.setLevel(LOGGING_LEVEL_FILE)

        # 日志输出格式
        file_formatter = logging.Formatter(
            fmt="[%(asctime)s.%(msecs)03d][%(levelname)s]:%(message)s  %(filename)s -> %(funcName)s line:%(lineno)d ",
            datefmt="%Y-%m-%d  %H:%M:%S",
        )
        console_formatter = colorlog.ColoredFormatter(
            fmt="%(log_color)s%(asctime) s[%(levelname)s] %(message)s [%(filename)s->%(funcName)s L:%(lineno)d]",
            datefmt="%Y-%m-%d %H:%M:%S",
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
